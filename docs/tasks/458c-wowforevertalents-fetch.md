# Task #458 (part 3): fetch a class's pages into an immutable snapshot

Make `tests/test_wowforevertalents.py` pass (14 tests) without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/sources/wowforevertalents.py`. No network: the tests pass a fake `http_get`.
- Before you start, the three `fetch` tests at the end of the test file fail (`fetch` doesn't exist yet); the other 11 pass.
- Run `.venv/Scripts/python -m pytest tests/test_wowforevertalents.py -q` after each step, then the fast suite once.

## Why
`update` needs the rank text for a class: the class page plus every talent page it links, fetched a polite 1.5 s apart,
kept as a raw snapshot (never changed once saved, so a second run reads the files instead of the site), with a
manifest. The game build comes from the talent pages' "Forever client build 1.60.x.y" source line.

## Step 1: imports
Replace the lines
```python
import html
import re
```
with
```python
import hashlib
import html
import json
import re
import time
from collections.abc import Callable
```
and add `from pathlib import Path` right after `from dataclasses import dataclass`.

## Step 2: add at the end of the file
```python
CLIENT_BUILD = re.compile(r"Forever client build (1\.60\.\d+\.\d+)")
```

## Step 3: add at the end of the file
```python
def fetch(class_slug: str, *, http_get: Callable[[str], str], raw_dir: Path, delay: float = 1.5,
          sleep: Callable[[float], None] = time.sleep) -> tuple[Path, WftPage]:
    """A class page and every talent page it links, saved under `raw_dir/<class>/` (immutable: a saved snapshot is
    read back instead of fetched again), as the page normalize reads. `raw_dir`'s name is the data version."""
    folder = raw_dir / class_slug
    class_path = folder / "class.html"
    if not class_path.exists():
        class_html = http_get(f"{BASE_URL}/{class_slug}/")
        pages = {}
        for slug in talent_slugs(class_html, class_slug):
            sleep(delay)
            pages[slug] = http_get(talent_url(class_slug, slug))
        (folder / "talents").mkdir(parents=True, exist_ok=True)
        for slug, text in pages.items():
            (folder / "talents" / f"{slug}.html").write_text(text, encoding="utf-8", newline="")
        class_path.write_text(class_html, encoding="utf-8", newline="")
    class_html = class_path.read_text(encoding="utf-8")
    talents = {}
    builds = []
    for slug in talent_slugs(class_html, class_slug):
        talent = parse_talent((folder / "talents" / f"{slug}.html").read_text(encoding="utf-8"))
        talents[talent.name] = talent
        builds += [m.group(1) for line in talent.sources for m in [CLIENT_BUILD.search(line)] if m]
    if not builds:
        raise ValueError(f"{class_slug}: no client build on any talent page")
    game_build = max(set(builds), key=builds.count)
    result = as_page(class_slug, class_html, talents, game_build=game_build, data_version=raw_dir.name)
    files = sorted(folder.rglob("*.html"))
    digest = hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest()
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps({
            "source": "wowforevertalents.com", "url": f"{BASE_URL}/{class_slug}/", "game_build": game_build,
            "pages": len(files), "sha256": digest,
        }, indent=1), encoding="utf-8", newline="\n")
    return manifest_path, result
```

## Done when
- `tests/test_wowforevertalents.py` passes (14 tests); the fast suite has no other new failures.
- Only `src/wowforever/sources/wowforevertalents.py` changed.
