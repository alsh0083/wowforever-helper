# Task #460 (part 1d): save snapshots of wowforeverbuilds.com and read them back as the guard's history

Make `tests/test_wowforeverbuilds.py` pass (26 tests) without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/sources/wowforeverbuilds.py`. No network: the tests pass a fake site.
- Before you start, the test file fails at import (`fetch`, `load_snapshot` and `load_history` don't exist yet).
  Nothing else should fail.
- Each step below replaces one block with another or adds one at the end of the file; copy them exactly. Apply them
  in order, top of the file first.
- Run `.venv/Scripts/python -m pytest tests/test_wowforeverbuilds.py -q` after the last step, then the fast suite once.

## Why
`standard_build` reads each guide code with the calculator it was made on, which takes every saved snapshot of the
site (#460). `fetch` saves one: each class's calculator (`/talents/<class>`), guide listing (`/guides/<class>`) and
spec guides (`/guide/<slug>`), gzipped (about 1.6 MB a snapshot instead of 11 MB; no gzip timestamp, so the same
page saves the same bytes) under `data/raw/wowforeverbuilds/<YYYYMMDD>/` with a manifest. A saved snapshot is
immutable (AGENTS.md): when its manifest exists, nothing is fetched. `load_snapshot` checks the pages against the
manifest's sha256 (of the uncompressed pages); `load_history` reads every saved snapshot, oldest first.

## Step 1
Replace
```python
import html
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
```
with
```python
import gzip
import hashlib
import html
import json
import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
```

## Step 2
Replace
```python
BASE_URL = "https://wowforeverbuilds.com"
```
with
```python
BASE_URL = "https://wowforeverbuilds.com"
CLASSES = ("druid", "hunter", "mage", "paladin", "priest", "rogue", "shaman", "warlock", "warrior")
```

## Step 3: add `fetch` at the end of the file
After the last line of `standard_build` (`    return ranks, ""`), add two blank lines and then:
```python
def fetch(*, http_get: Callable[[str], str], raw_dir: Path, classes: Sequence[str] = CLASSES, delay: float = 1.5,
          sleep: Callable[[float], None] = time.sleep) -> Path:
    """Each class's calculator, guide listing and spec guides, saved gzipped under `raw_dir` (named YYYYMMDD). A
    saved snapshot is immutable: when its manifest exists nothing is fetched. Returns the manifest's path."""
    manifest_path = raw_dir / "manifest.json"
    if manifest_path.exists():
        return manifest_path
    pages: dict[str, str] = {}
    for n, class_slug in enumerate(classes):
        if n:
            sleep(delay)
        pages[f"talents-{class_slug}.html"] = http_get(f"{BASE_URL}/talents/{class_slug}")
        sleep(delay)
        listing = http_get(f"{BASE_URL}/guides/{class_slug}")
        pages[f"guides-{class_slug}.html"] = listing
        for slug in guide_slugs(listing):
            sleep(delay)
            pages[f"guide-{slug}.html"] = http_get(f"{BASE_URL}/guide/{slug}")
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, text in pages.items():
        (raw_dir / f"{name}.gz").write_bytes(gzip.compress(text.encode("utf-8"), mtime=0))
    manifest_path.write_text(json.dumps({
        "source": "wowforeverbuilds.com", "url": BASE_URL, "captured": _date(raw_dir.name),
        "classes": list(classes), "pages": len(pages), "sha256": _digest(raw_dir),
    }, indent=1), encoding="utf-8", newline="\n")
    return manifest_path
```

## Step 4: add `_date`, `_read` and `_digest` at the end of the file
After the last line of `fetch` (`    return manifest_path`), add two blank lines and then:
```python
def _date(folder_name: str) -> str:
    return f"{folder_name[:4]}-{folder_name[4:6]}-{folder_name[6:]}"


def _read(path: Path) -> str:
    return gzip.decompress(path.read_bytes()).decode("utf-8")


def _digest(folder: Path) -> str:
    """sha256 of the pages as fetched (uncompressed), in file-name order."""
    pages = sorted(folder.glob("*.html.gz"))
    return hashlib.sha256(b"".join(gzip.decompress(p.read_bytes()) for p in pages)).hexdigest()
```

## Step 5: add `load_snapshot` and `load_history` at the end of the file
After the last line of `_digest`, add two blank lines and then:
```python
def load_snapshot(folder: Path) -> Snapshot:
    """A saved snapshot, checked against its manifest."""
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if _digest(folder) != manifest["sha256"]:
        raise ValueError(f"{folder}: pages changed since the snapshot was saved")
    calculators = {}
    for path in sorted(folder.glob("talents-*.html.gz")):
        calc = parse_calculator(_read(path))
        calculators[calc.class_slug] = calc
    guides = {}
    for path in sorted(folder.glob("guide-*.html.gz")):
        slug = path.name.removeprefix("guide-").removesuffix(".html.gz")
        guides[slug] = parse_guide(_read(path), slug)
    return Snapshot(manifest["captured"], calculators, guides)


def load_history(root: Path) -> list[Snapshot]:
    """Every saved snapshot under `root` (`data/raw/wowforeverbuilds/`), oldest first."""
    folders = [f for f in root.iterdir() if re.fullmatch(r"\d{8}", f.name) and (f / "manifest.json").exists()]
    return [load_snapshot(f) for f in sorted(folders, key=lambda f: f.name)]
```

## Done when
- `tests/test_wowforeverbuilds.py` passes (26 tests); the fast suite has no other new failures.
- Only `src/wowforever/sources/wowforeverbuilds.py` changed.
