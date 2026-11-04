# Task #460 (part F): pick one sourced community build per slot, and the import tool

Make `tests/test_sourced.py` pass. Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Create `src/wowforever/sourced.py` and `tools/import_sourced_builds.py`, and edit
  `config/consensus.toml`. No network: do not run the tool.
- Before you start, `tests/test_sourced.py` fails to import `wowforever.sourced`.
- Run `.venv/Scripts/python -m pytest tests/test_sourced.py -q` at the end. Do not run the fast suite: other 70755
  tasks leave failures there that are expected.
- Steps 1 and 2 create new files: use `*** Add File:` and copy the content exactly, one `+` per line.
  Step 3 replaces one line with three; copy both exactly.

## Why
Owner, 2026-10-31 (#460): community standards only from a current source. Each slot (archetype x focus) takes the
wowforeverbuilds.com spec guide build when the guard keeps it, then talentsforever.com's most saved complete top build
that lands in the slot (PvE only), else nothing (the model build holds the slot). Builds are taken as published or
dropped, never adjusted. The tool deletes a class's non-hand builds and writes the sourced ones; the model, pick and
leveling builds are derived again afterwards with the existing tools.

## Step 1: create `src/wowforever/sourced.py`
```python
"""Community standards from current sources (#460; owner, 2026-10-31: "only have the standards that you can source").

Each slot (archetype x focus) takes, in order:
1. wowforeverbuilds.com's spec guide build for that focus, when `standard_build` keeps it;
2. talentsforever.com's most saved top build whose talents land in the slot (PvE only: the site doesn't say what a
   build is for);
3. nothing: the slot's model build holds it.
A build is taken as published. A talent our trees don't have, a rank over its cap, unspent points, or a build that
isn't legal at 60 drops it; nothing is adjusted.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from wowforever.rules import check_build, points_available
from wowforever.schema import ClassData
from wowforever.shortlist import classify


@dataclass(frozen=True)
class Sourced:
    archetype: str
    focus: str                     # "PvE" or "PvP"
    ranks: Mapping[str, int]       # talent name -> rank, as published
    source: str                    # "wowforeverbuilds.com" or "talentsforever.com"
    url: str
    title: str                     # the guide's title, or the site's build name
    note: str                      # where it ranks on the site


@dataclass(frozen=True)
class Candidate:
    focus: str | None              # None when the source doesn't say (talentsforever.com)
    ranks: Mapping[str, int]
    source: str
    url: str
    title: str
    note: str


def on_our_trees(ranks: Mapping[str, int], cls: ClassData) -> tuple[dict[int, int] | None, str]:
    """`ranks` by talent id when every talent is ours and within its cap, all points are spent and the build is legal
    at 60; otherwise (None, why)."""
    by_name = {t.name: t for t in cls.talents}
    for name, rank in ranks.items():
        talent = by_name.get(name)
        if talent is None:
            return None, f"{name}: not a talent on our trees"
        if rank > talent.max_rank:
            return None, f"{name}: rank {rank} is over its cap {talent.max_rank}"
    ids = {by_name[name].talent_id: rank for name, rank in ranks.items()}
    level = cls.rules.max_level
    spent, available = sum(ids.values()), points_available(level, cls.rules)
    if spent != available:
        return None, f"spends {spent} of {available} points"
    errors = check_build(cls, ids, level)
    return (None, "not legal: " + "; ".join(errors)) if errors else (ids, "")


def pick(cls: ClassData, guides: Sequence[Candidate], top: Sequence[Candidate], *, deep: int, hybrid: int,
         recognized: tuple[str, ...]) -> tuple[list[Sourced], list[str]]:
    """One community build per slot, guides first, then the top builds in the order given (most saved first).
    Returns the builds and a line for each candidate left out."""
    chosen: dict[tuple[str, str], Sourced] = {}
    skipped: list[str] = []
    for candidate in [*guides, *top]:
        ids, why = on_our_trees(candidate.ranks, cls)
        if ids is None:
            skipped.append(f"{candidate.title}: {why}")
            continue
        archetype = classify(cls, ids, deep=deep, hybrid=hybrid, recognized=recognized)
        if archetype is None:
            skipped.append(f"{candidate.title}: no archetype (points {_split(cls, ids)})")
            continue
        slot = (archetype, candidate.focus or "PvE")
        if slot in chosen:
            skipped.append(f"{candidate.title}: {archetype} {slot[1]} already has {chosen[slot].title}")
            continue
        chosen[slot] = Sourced(archetype, slot[1], dict(candidate.ranks), candidate.source, candidate.url,
                               candidate.title, candidate.note)
    return list(chosen.values()), skipped


def _split(cls: ClassData, ids: Mapping[int, int]) -> str:
    return "/".join(str(sum(ids.get(t, 0) for t in tree.talent_ids)) for tree in cls.trees)


SOURCE_KEYS = {"wowforeverbuilds.com": "wowforeverbuilds_guides", "talentsforever.com": "talentsforever_top"}


def build_toml(class_name: str, s: Sourced, captured: str) -> tuple[str, str]:
    """(build id, file text) for config/builds/: the build as published, labelled with where it came from."""
    tree = s.archetype.removeprefix("deep ")
    pair = f"{class_name}-" + tree.lower().replace("/", "-").replace(" ", "-")
    build_id = pair + ("-pvp" if s.focus == "PvP" else "")
    credit = " Data (c) Talents Forever, https://talentsforever.com, CC BY 4.0." if s.source == "talentsforever.com" else ""
    lines = [f"# Community standard (#460) from {s.source}, saved {captured}: {s.note}.{credit}",
             f"# {s.url}",
             "# Taken as published: tools/import_sourced_builds.py replaces it, never adjusts it.", "",
             f'id = "{build_id}"', f'class = "{class_name}"', f"name = {json.dumps(f'{tree} ({s.focus})')}",
             f'pair = "{pair}"', f'variant = "{s.focus}"', 'origin = "community"', f'sources = ["{SOURCE_KEYS[s.source]}"]',
             'confidence = "medium"', f"summary = {json.dumps(f'{s.title} ({s.source}, {s.note}).')}", "", "[final]"]
    lines += [f"{json.dumps(name)} = {rank}" for name, rank in sorted(s.ranks.items())]
    return build_id, "\n".join(lines) + "\n"
```

## Step 2: create `tools/import_sourced_builds.py`
```python
"""Replace each class's builds with community standards from current sources (#460).

Owner, 2026-10-31: "ditch any builds I forced you to hold onto before and only have the standards that you can
source". For every class this saves today's wowforeverbuilds.com and talentsforever.com snapshots (once; both
robots-allowed), deletes every build in config/builds/ for the class that isn't hand-made, and writes one community
build per slot that a source fills (src/wowforever/sourced.py). The model builds, model picks and leveling builds
are derived again afterwards:

    .venv/Scripts/python tools/import_sourced_builds.py [class ...]
    .venv/Scripts/python -m wowforever report --class <class>      # every class
    .venv/Scripts/python tools/derive_slot_builds.py
    .venv/Scripts/python tools/derive_model_picks.py
    .venv/Scripts/python tools/derive_leveling_builds.py <class ...>
    then the reports and the dashboard again (docs/patch-update.md).
"""
from __future__ import annotations

import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from wowforever.classes import CLASSES, class_module
from wowforever.consensus import Consensus
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.sourced import SOURCE_KEYS, Candidate, build_toml, pick
from wowforever.sources import talentsforever as tf
from wowforever.sources import wowforeverbuilds as wfb
from wowforever.sources.http import http_get

ROOT = Path(__file__).resolve().parents[1]
BUILDS = ROOT / "config" / "builds"
RAW = ROOT / "data" / "raw"


def candidates(class_name, cls, history, snapshot):
    guides = []
    for slug, guide in sorted(history[-1].guides.items()):
        if guide.class_slug != class_name:
            continue
        ranks, why = wfb.standard_build(slug, history, cls)
        if ranks is None:
            print(f"  guide left out: {why}")
            continue
        guides.append(Candidate("PvP" if "-pvp-" in slug else "PvE", ranks, "wowforeverbuilds.com", guide.url,
                                guide.title, "spec guide"))
    page, export = snapshot[class_name]
    window = tf.parse_builds_page(page)["window"]
    rows = sorted(tf.popular_builds(page, export), key=lambda row: -row["saved_total"])
    top = [Candidate(None, row["final"], "talentsforever.com", f"{tf.BASE_URL}/{class_name}/60/{row['code']}",
                     row["name"], f"top build #{row['rank']}{f' {window}' if window else ''}, saved {row['saved_total']}")
           for row in rows]
    return guides, top


def run(classes) -> int:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    wfb.fetch(http_get=http_get, raw_dir=RAW / "wowforeverbuilds" / today)
    tf.fetch(http_get=http_get, raw_dir=RAW / "talentsforever" / today)
    history = wfb.load_history(RAW / "wowforeverbuilds")
    folder = tf.latest_snapshot(RAW / "talentsforever")
    snapshot = tf.load_snapshot(folder)
    captured = f"{folder.name[:4]}-{folder.name[4:6]}-{folder.name[6:]}"
    consensus = Consensus.load()
    missing = [key for key in SOURCE_KEYS.values() if key not in consensus.sources]
    if missing:
        raise SystemExit(f"config/consensus.toml has no [sources] entry for {', '.join(missing)}")
    arch = consensus.archetypes
    ds = Dataset.load(latest_dataset_path())
    written = 0
    for class_name in classes:
        cls = ds.class_data(class_name)
        print(f"[{class_name}]")
        for path in sorted(BUILDS.glob(f"{class_name}-*.toml")):
            if tomllib.loads(path.read_text(encoding="utf-8")).get("origin", "hand") != "hand":
                path.unlink()
        guides, top = candidates(class_name, cls, history, snapshot)
        chosen, skipped = pick(cls, guides, top, deep=arch["deep"], hybrid=arch["hybrid"],
                               recognized=tuple(getattr(class_module(class_name), "HYBRIDS", ())))
        for line in skipped:
            print(f"  left out: {line}")
        for s in chosen:
            build_id, text = build_toml(class_name, s, captured)
            (BUILDS / f"{build_id}.toml").write_text(text, encoding="utf-8", newline="\n")
            print(f"  wrote {build_id}: {s.title} ({s.source}, {s.note})")
            written += 1
    return written


if __name__ == "__main__":
    print(f"{run(sys.argv[1:] or CLASSES)} community builds written")
```

## Step 3: `config/consensus.toml`
Replace
```toml
[sources]
```
with
```toml
[sources]
wowforeverbuilds_guides = { url = "https://wowforeverbuilds.com/guides/", kind = "guide", era = "forever", date = "2026-11-04", note = "Spec guides with a talent build each (PvE and PvP per spec), read from the site's calculator codes; kept only while the guide's trees, rank text and legality match the current build (#460, #463)." }
talentsforever_top = { url = "https://talentsforever.com/", kind = "popularity", era = "forever", date = "2026-11-04", note = "Each class's five most shared builds since the last talent change, with save counts; data (c) Talents Forever, CC BY 4.0. The most saved complete build legal on our trees fills an empty PvE slot (#460)." }
```
