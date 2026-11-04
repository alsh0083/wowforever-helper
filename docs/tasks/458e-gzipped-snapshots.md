# Task #458 (part E): save wowforevertalents.com snapshots gzipped

Make `tests/test_wowforevertalents.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/sources/wowforevertalents.py`. No network.
- Before you start, `test_fetch_snapshots_the_class_and_returns_the_page` and
  `test_a_plain_html_snapshot_from_before_458_still_reads_offline` fail; the others pass.
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.
- Run `.venv/Scripts/python -m pytest tests/test_wowforevertalents.py -q` at the end, then the fast suite once.

## Why
A full wowforevertalents.com snapshot is about 18 MB of HTML; the other sources are saved gzipped (`mtime=0`, the
checksum over the uncompressed pages). Saved snapshots are immutable, so the plain `.html` pages of older snapshots
keep reading as before.


## Step 1: `src/wowforever/sources/wowforevertalents.py`
Replace
```python

import hashlib
```
with
```python

import gzip
import hashlib
```

## Step 2: `src/wowforever/sources/wowforevertalents.py`
Replace
```python

def fetch(class_slug: str, *, http_get: Callable[[str], str], raw_dir: Path, delay: float = 1.5,
```
with
```python

def _page(path: Path) -> Path:
    """A saved page: `<name>.html.gz` (since #458), else the plain `<name>.html` of older snapshots."""
    gz = path.with_name(path.name + ".gz")
    return gz if gz.exists() or not path.exists() else path


def _bytes(path: Path) -> bytes:
    return gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()


def _read(path: Path) -> str:
    return _bytes(_page(path)).decode("utf-8")

def fetch(class_slug: str, *, http_get: Callable[[str], str], raw_dir: Path, delay: float = 1.5,
```

## Step 3: `src/wowforever/sources/wowforevertalents.py`
Replace
```python
    folder = raw_dir / class_slug
    class_path = folder / "class.html"
    if not class_path.exists():
        class_html = http_get(f"{BASE_URL}/{class_slug}/")
```
with
```python
    folder = raw_dir / class_slug
    if not _page(folder / "class.html").exists():
        class_html = http_get(f"{BASE_URL}/{class_slug}/")
```

## Step 4: `src/wowforever/sources/wowforevertalents.py`
Replace
```python
        (folder / "talents").mkdir(parents=True, exist_ok=True)
        for slug, text in pages.items():
            (folder / "talents" / f"{slug}.html").write_text(text, encoding="utf-8", newline="")
        class_path.write_text(class_html, encoding="utf-8", newline="")
    class_html = class_path.read_text(encoding="utf-8")
    talents = {}
```
with
```python
        (folder / "talents").mkdir(parents=True, exist_ok=True)
        for slug, text in pages.items():       # gzipped since #458 (a class's pages are about 2 MB of HTML)
            (folder / "talents" / f"{slug}.html.gz").write_bytes(gzip.compress(text.encode("utf-8"), mtime=0))
        (folder / "class.html.gz").write_bytes(gzip.compress(class_html.encode("utf-8"), mtime=0))
    class_html = _read(folder / "class.html")
    talents = {}
```

## Step 5: `src/wowforever/sources/wowforevertalents.py`
Replace
```python
    for slug in talent_slugs(class_html, class_slug):
        talent = parse_talent((folder / "talents" / f"{slug}.html").read_text(encoding="utf-8"))
        talents[talent.name] = talent
```
with
```python
    for slug in talent_slugs(class_html, class_slug):
        talent = parse_talent(_read(folder / "talents" / f"{slug}.html"))
        talents[talent.name] = talent
```

## Step 6: `src/wowforever/sources/wowforevertalents.py`
Replace
```python
    result = as_page(class_slug, class_html, talents, game_build=game_build, data_version=raw_dir.name)
    files = sorted(folder.rglob("*.html"))
    digest = hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest()
    manifest_path = folder / "manifest.json"
```
with
```python
    result = as_page(class_slug, class_html, talents, game_build=game_build, data_version=raw_dir.name)
    files = sorted(folder.rglob("*.html")) or sorted(folder.rglob("*.html.gz"))
    digest = hashlib.sha256(b"".join(_bytes(p) for p in files)).hexdigest()
    manifest_path = folder / "manifest.json"
```
