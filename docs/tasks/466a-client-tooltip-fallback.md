# Task #466 (part A): rank text from the client tooltip when wowforevertalents.com serves no page for a talent

Make `tests/test_client_text.py`, `tests/test_wowforevertalents.py` and `tests/test_update.py` pass without
breaking the rest of the fast suite. Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Create `src/wowforever/client_text.py`; edit `src/wowforever/sources/wowforevertalents.py`
  and `src/wowforever/update.py`. No network.
- Before you start, `tests/test_client_text.py` can't import `wowforever.client_text`, and the fallback tests in the
  other two files fail.
- Step 1 creates a new file: use `*** Add File:` and copy the content exactly, one `+` per line. The other steps
  replace one block with another; copy both exactly, including blank lines. Apply them in order.
- Run `.venv/Scripts/python -m pytest tests/test_client_text.py tests/test_wowforevertalents.py tests/test_update.py -q`
  at the end, then the fast suite once.

## Why
wowforevertalents.com's shaman page links `/shaman/talents/call-of-thunder/` and serves the class page there, so
shaman's 70755 rank text can't be read and shaman stays on 70707 data (#466). Call of Thunder is in the client:
its tooltip "... by $s1%." with effect 0 at 5. For a talent the site serves no page for, the update now takes a
one-rank talent's text from the client tooltip. It reads the tables before the page fetch, so the fallback can use
them. Anything the tooltip can't fill stops the update as before.

## Step 1: create `src/wowforever/client_text.py`
```python
"""Talent rank text from the client's own tooltip (#466): the fallback when wowforevertalents.com links a talent but
serves no page for it (Call of Thunder, 4 Nov). Only a one-rank talent whose tooltip uses nothing but `$sN` (effect
N's base points) is rendered; anything else stays unread and the update stops as before."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_EFFECT = re.compile(r"\$s(\d)")


def render(description: str, base_points: Mapping[int, float]) -> str | None:
    """`description` with each `$sN` replaced by effect N's base points, or None if any token is left."""
    def value(match: re.Match[str]) -> str:
        points = base_points.get(int(match.group(1)) - 1)
        return match.group(0) if points is None else f"{abs(points):g}"

    text = _EFFECT.sub(value, description)
    return None if "$" in text else text


def talent_texts(tables: Mapping[str, Any], name: str) -> tuple[str, ...] | None:
    """The rank text of the one-rank trait talent `name`, from its spell's tooltip, or None."""
    ids = {int(r["ID"]) for r in tables["SpellName"] if r["Name_lang"] == name}
    spells = sorted(ids & {int(r["SpellID"]) for r in tables["TraitDefinition"]})
    if len(spells) != 1:
        return None
    spell_id = spells[0]
    description = next((r["Description_lang"] for r in tables["Spell"] if int(r["ID"]) == spell_id), "")
    points = {int(r["EffectIndex"]): float(r["EffectBasePointsF"]) for r in tables["SpellEffect"]
              if int(r["SpellID"]) == spell_id}
    text = render(description, points) if description else None
    return (text,) if text else None
```n
## Step 2: `src/wowforever/sources/wowforevertalents.py`
Replace
```python
def as_page(class_slug: str, class_html: str, talents: dict[str, TalentPage], *, game_build: str,
            data_version: str) -> WftPage:
    """The class page's grid with every talent's rank text, in the shape normalize and crosscheck read."""
    trees = class_trees(class_html)
```
with
```python
def as_page(class_slug: str, class_html: str, talents: dict[str, TalentPage], *, game_build: str,
            data_version: str, fallback: Callable[[str], tuple[str, ...] | None] | None = None) -> WftPage:
    """The class page's grid with every talent's rank text, in the shape normalize and crosscheck read. A talent
    the site has no page for takes `fallback`'s rank text (the client tooltip, #466) when it has as many ranks."""
    trees = class_trees(class_html)
```

## Step 3: `src/wowforever/sources/wowforevertalents.py`
Replace
```python
            found = talents.get(talent["name"])
            if found is None:
```
with
```python
            found = talents.get(talent["name"])
            texts = fallback(talent["name"]) if found is None and fallback is not None else None
            if found is None and texts is not None and len(texts) == talent["maxRank"]:
                found = TalentPage(talent["name"], class_slug.title(), tree["name"], talent["maxRank"], texts,
                                   ("Forever client tooltip: wowforevertalents.com serves no page for it",))
            if found is None:
```

## Step 4: `src/wowforever/sources/wowforevertalents.py`
Replace
```python
def fetch(class_slug: str, *, http_get: Callable[[str], str], raw_dir: Path, delay: float = 1.5,
          sleep: Callable[[float], None] = time.sleep) -> tuple[Path, WftPage]:
    """A class page and every talent page it links, saved under `raw_dir/<class>/` (immutable: a saved snapshot is
```
with
```python
def fetch(class_slug: str, *, http_get: Callable[[str], str], raw_dir: Path, delay: float = 1.5,
          sleep: Callable[[float], None] = time.sleep,
          fallback: Callable[[str], tuple[str, ...] | None] | None = None) -> tuple[Path, WftPage]:
    """A class page and every talent page it links, saved under `raw_dir/<class>/` (immutable: a saved snapshot is
```

## Step 5: `src/wowforever/sources/wowforevertalents.py`
Replace
```python
    for slug in talent_slugs(class_html, class_slug):
        talent = parse_talent(_read(folder / "talents" / f"{slug}.html"))
        talents[talent.name] = talent
```
with
```python
    for slug in talent_slugs(class_html, class_slug):
        try:
            talent = parse_talent(_read(folder / "talents" / f"{slug}.html"))
        except ValueError:
            if fallback is None:
                raise
            continue                   # the site linked it but served another page (#466): `fallback` fills it in
        talents[talent.name] = talent
```

## Step 6: `src/wowforever/sources/wowforevertalents.py`
Replace
```python
    game_build = max(set(builds), key=builds.count)
    result = as_page(class_slug, class_html, talents, game_build=game_build, data_version=raw_dir.name)
    files = sorted(folder.rglob("*.html")) or sorted(folder.rglob("*.html.gz"))
```
with
```python
    game_build = max(set(builds), key=builds.count)
    result = as_page(class_slug, class_html, talents, game_build=game_build, data_version=raw_dir.name,
                     fallback=fallback)
    files = sorted(folder.rglob("*.html")) or sorted(folder.rglob("*.html.gz"))
```

## Step 7: `src/wowforever/update.py`
Replace
```python
from wowforever.revisions import Change
from wowforever.schema import ClassData, Dataset, Provenance
```
with
```python
from wowforever.revisions import Change
from wowforever import client_text
from wowforever.schema import ClassData, Dataset, Provenance
```

## Step 8: `src/wowforever/update.py`
Replace
```python
    module = class_module(class_name)
    if rank_text_source == "wowforevertalents":
```
with
```python
    module = class_module(class_name)
    tables_dir = data_dir / "cache" / "wago" / build
    extra_provenance: tuple[Provenance, ...] = ()
    if hotfixes is not None:
        overlay_dir = data_dir / "cache" / "hotfixed" / hotfixes.name
        hotfixes_module.overlay_build(tables_dir, overlay_dir, build, hotfix_entries)
        tables_dir = overlay_dir
        manifest = json.loads((hotfixes / "manifest.json").read_text(encoding="utf-8"))
        extra_provenance = (Provenance(
            source="client hotfix cache", game_build=build, data_version=hotfixes.name,
            fetched_at=manifest["captured_at"], snapshot_sha256=manifest["sha256"],
        ),)
    tables = normalize_module.read_tables(tables_dir)
    if rank_text_source == "wowforevertalents":
```

## Step 9: `src/wowforever/update.py`
Replace
```python
        raw_dir = data_dir / "raw" / "wowforevertalents" / now[:10].replace("-", "")
        page_manifest, page = wowforevertalents.fetch(class_name, http_get=http_get, raw_dir=raw_dir, delay=delay)
        page_provenance = Provenance(
```
with
```python
        raw_dir = data_dir / "raw" / "wowforevertalents" / now[:10].replace("-", "")
        # a talent the site links but serves no page for takes the client tooltip (#466)
        page_manifest, page = wowforevertalents.fetch(class_name, http_get=http_get, raw_dir=raw_dir, delay=delay,
                                                      fallback=lambda name: client_text.talent_texts(tables, name))
        page_provenance = Provenance(
```

## Step 10: `src/wowforever/update.py`
Replace
```python

    tables_dir = data_dir / "cache" / "wago" / build
    extra_provenance: tuple[Provenance, ...] = ()
    if hotfixes is not None:
        overlay_dir = data_dir / "cache" / "hotfixed" / hotfixes.name
        hotfixes_module.overlay_build(tables_dir, overlay_dir, build, hotfix_entries)
        tables_dir = overlay_dir
        manifest = json.loads((hotfixes / "manifest.json").read_text(encoding="utf-8"))
        extra_provenance = (Provenance(
            source="client hotfix cache", game_build=build, data_version=hotfixes.name,
            fetched_at=manifest["captured_at"], snapshot_sha256=manifest["sha256"],
        ),)
    tables = normalize_module.read_tables(tables_dir)
    cls, report = normalize_module.normalize_class(tables, module.LAYOUT, page, wago_build=build,
```
with
```python


    cls, report = normalize_module.normalize_class(tables, module.LAYOUT, page, wago_build=build,
```
