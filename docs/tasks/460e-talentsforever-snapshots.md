# Task #460 (part E): save talentsforever.com snapshots

Make `tests/test_talentsforever.py` pass without breaking the rest of the fast suite. Do not edit the tests or
anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/sources/talentsforever.py`. No network.
- Before you start, the two snapshot tests at the end of `tests/test_talentsforever.py` fail; the others pass.
- Run `.venv/Scripts/python -m pytest tests/test_talentsforever.py -q` at the end. Do not run the fast suite: other
  70755 tasks leave failures there that are expected.
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.

## Why
The import of community standards (#460) reads talentsforever.com's top builds. Like every raw source, the pages are
saved first (gzipped, immutable, with a checksum) and the import reads the saved copy.

## Step 1: `src/wowforever/sources/talentsforever.py`
Replace
```python

import html
```
with
```python

import gzip
import hashlib
import html
```

## Step 2: `src/wowforever/sources/talentsforever.py`
Replace
```python
import html
import re
```
with
```python
import html
import json
import re
```

## Step 3: `src/wowforever/sources/talentsforever.py`
Replace
```python
import re
from typing import Any
```
with
```python
import re
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
```

## Step 4: `src/wowforever/sources/talentsforever.py`
Replace
```python
    return [dict(row, final=decode_build(row["code"], export)) for row in rows]
```
with
```python
    return [dict(row, final=decode_build(row["code"], export)) for row in rows]


# ---- snapshots (#460): each class's builds page and export, saved gzipped and immutable ----

BASE_URL = "https://talentsforever.com"
CLASSES = ("druid", "hunter", "mage", "paladin", "priest", "rogue", "shaman", "warlock", "warrior")


def _digest(folder: Path) -> str:
    sha = hashlib.sha256()
    for path in sorted(folder.glob("*.gz")):
        sha.update(gzip.decompress(path.read_bytes()))
    return sha.hexdigest()


def fetch(*, http_get: Callable[[str], str], raw_dir: Path, classes: Sequence[str] = CLASSES, delay: float = 1.5,
          sleep: Callable[[float], None] = time.sleep) -> Path:
    """Each class's /<class>/builds page and /export/<class>.json, saved gzipped under `raw_dir` (named YYYYMMDD).
    A saved snapshot is immutable: when its manifest exists nothing is fetched. Returns the manifest's path."""
    manifest_path = raw_dir / "manifest.json"
    if manifest_path.exists():
        return manifest_path
    files: dict[str, str] = {}
    for n, class_slug in enumerate(classes):
        if n:
            sleep(delay)
        files[f"builds-{class_slug}.html"] = http_get(f"{BASE_URL}/{class_slug}/builds")
        sleep(delay)
        files[f"export-{class_slug}.json"] = http_get(f"{BASE_URL}/export/{class_slug}.json")
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (raw_dir / f"{name}.gz").write_bytes(gzip.compress(text.encode("utf-8"), mtime=0))
    name = raw_dir.name
    manifest_path.write_text(json.dumps({
        "source": SOURCE, "url": BASE_URL, "captured": f"{name[:4]}-{name[4:6]}-{name[6:]}", "classes": list(classes),
        "files": len(files), "sha256": _digest(raw_dir), "license": "CC BY 4.0",
    }, indent=1) + "\n", encoding="utf-8", newline="\n")
    return manifest_path


def load_snapshot(folder: Path) -> dict[str, tuple[str, dict[str, Any]]]:
    """A saved snapshot as {class: (builds page, export)}; refuses pages edited since they were saved."""
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if _digest(folder) != manifest["sha256"]:
        raise ValueError(f"{folder}: pages changed since the snapshot was saved")
    read = lambda name: gzip.decompress((folder / f"{name}.gz").read_bytes()).decode("utf-8")
    return {c: (read(f"builds-{c}.html"), json.loads(read(f"export-{c}.json"))) for c in manifest["classes"]}


def latest_snapshot(root: Path) -> Path | None:
    """The newest saved snapshot folder under `root` (YYYYMMDD names), or None."""
    folders = sorted(p for p in root.glob("[0-9]" * 8) if (p / "manifest.json").exists())
    return folders[-1] if folders else None
```
