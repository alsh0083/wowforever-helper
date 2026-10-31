# Task #456 (part B2) + #458 (part 4): `update` applies a hotfix snapshot and can take rank text from wowforevertalents.com

Make `tests/test_update.py` pass (12 tests) without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/update.py` and `src/wowforever/__main__.py`. No network.
- Before you start, the last five tests in `tests/test_update.py` fail; the other seven pass.
- Each step below replaces one block with another; copy both exactly. Apply them in order, top of each file first.
- Run `.venv/Scripts/python -m pytest tests/test_update.py -q` after the `update.py` steps and again at the end, then the fast suite once.

## Why
The launch build is 1.60.1.70707 plus server hotfixes that exist only in the client's hotfix cache (#456), and
wowforevertalent.com's rank text is stuck on 70425 (#458). `check_for_updates` gains `hotfixes` (a saved snapshot folder:
its rows are applied to the tables, `sources/hotfixes.overlay_build`) and `rank_text_source` (`wowforevertalents` reads
`sources/wowforevertalents.fetch`). The CLI gets `--hotfixes` and `--rank-text`.

## Step 1: `src/wowforever/update.py`
Replace
```python
from wowforever.schema import ClassData, Dataset, Provenance
from wowforever.sources import wago, wowforevertalent
from wowforever.sources.http import http_get as default_http_get
```
with
```python
from wowforever.schema import ClassData, Dataset, Provenance
from wowforever.sources import hotfixes as hotfixes_module
from wowforever.sources import wago, wowforevertalent, wowforevertalents
from wowforever.sources.http import http_get as default_http_get
```

## Step 2: `src/wowforever/update.py`
Replace
```python
WAGO_BUILDS_URL = "https://wago.tools/api/builds"
MAX_LISTED_CHANGES = 20
```
with
```python
WAGO_BUILDS_URL = "https://wago.tools/api/builds"
RANK_TEXT_SOURCES = ("wowforevertalent", "wowforevertalents")
MAX_LISTED_CHANGES = 20
```

## Step 3: `src/wowforever/update.py`
Replace
```python
    file_get: Callable[[str], bytes] | None = None,
) -> UpdateSummary:
```
with
```python
    file_get: Callable[[str], bytes] | None = None,
    hotfixes: Path | None = None,
    rank_text_source: str = "wowforevertalent",
) -> UpdateSummary:
```

## Step 4: `src/wowforever/update.py`
Replace
```python
    for every timestamp.
    """
```
with
```python
    for every timestamp.

    `hotfixes` is a saved hotfix snapshot (`data/raw/hotfixes/<build>-<date>/`: the client's DBCache.bin and a
    manifest, #456): its rows are applied to the build's tables first. `rank_text_source` picks where talent rank
    text comes from: wowforevertalent.com (default) or wowforevertalents.com (#458).
    """
```

## Step 5: `src/wowforever/update.py`
Replace
```python
    """
    if now is None:
```
with
```python
    """
    if rank_text_source not in RANK_TEXT_SOURCES:
        raise ValueError(f"unknown rank text source {rank_text_source!r}")
    if now is None:
```

## Step 6: `src/wowforever/update.py`
Replace
```python
    build = wago.latest_build(json.loads(http_get(WAGO_BUILDS_URL)))
    # table CSVs aren't in wago.tools' published API: missing ones are read from the game files
```
with
```python
    build = wago.latest_build(json.loads(http_get(WAGO_BUILDS_URL)))
    hotfix_entries = None
    if hotfixes is not None:
        cache_build, hotfix_entries = hotfixes_module.read_cache((hotfixes / "DBCache.bin").read_bytes())
        if str(cache_build) != build.rsplit(".", 1)[1]:
            raise ValueError(f"hotfix cache is for build {cache_build}; the latest build is {build}")
    # table CSVs aren't in wago.tools' published API: missing ones are read from the game files
```

## Step 7: `src/wowforever/update.py`
Replace
```python
    module = class_module(class_name)
    page_path, page = wowforevertalent.fetch(
        class_name, http_get=http_get, raw_dir=data_dir / "raw" / "wowforevertalent"
    )

```
with
```python
    module = class_module(class_name)
    if rank_text_source == "wowforevertalents":
        raw_dir = data_dir / "raw" / "wowforevertalents" / now[:10].replace("-", "")
        page_manifest, page = wowforevertalents.fetch(class_name, http_get=http_get, raw_dir=raw_dir, delay=delay)
        page_provenance = Provenance(
            source="wowforevertalents.com", game_build=page.game_build, data_version=page.page_data_version,
            fetched_at=now, snapshot_sha256=json.loads(page_manifest.read_text(encoding="utf-8"))["sha256"],
        )
    else:
        page_path, page = wowforevertalent.fetch(
            class_name, http_get=http_get, raw_dir=data_dir / "raw" / "wowforevertalent"
        )
        page_provenance = Provenance(
            source=wowforevertalent.SOURCE, game_build=page.game_build, data_version=page.page_data_version,
            fetched_at=now, snapshot_sha256=wowforevertalent.manifest_for(page_path)["sha256"],
        )

```

## Step 8: `src/wowforever/update.py`
Replace
```python

    tables = normalize_module.read_tables(data_dir / "cache" / "wago" / build)
    cls, report = normalize_module.normalize_class(tables, module.LAYOUT, page, wago_build=build,
```
with
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

## Step 9: `src/wowforever/update.py`
Replace
```python

    wft_manifest = wowforevertalent.manifest_for(page_path)
    dataset = Dataset(
```
with
```python

    dataset = Dataset(
```

## Step 10: `src/wowforever/update.py`
Replace
```python
            ),
            Provenance(
                source=wowforevertalent.SOURCE,
                game_build=page.game_build,
                data_version=page.page_data_version,
                fetched_at=now,
                snapshot_sha256=wft_manifest["sha256"],
            ),
        ),
```
with
```python
            ),
            page_provenance,
            *extra_provenance,
        ),
```

## Step 11: `src/wowforever/__main__.py`
Replace
```python
    upd.add_argument("--delay", type=float, default=1.0, help="seconds between table downloads")
    pr = sub.add_parser("patch-readiness",
```
with
```python
    upd.add_argument("--delay", type=float, default=1.0, help="seconds between table downloads")
    upd.add_argument("--hotfixes", help="saved hotfix snapshot folder to apply (data/raw/hotfixes/<build>-<date>, #456)")
    upd.add_argument("--rank-text", default="wowforevertalent", choices=("wowforevertalent", "wowforevertalents"),
                     help="where talent rank text comes from (#458)")
    pr = sub.add_parser("patch-readiness",
```

## Step 12: `src/wowforever/__main__.py`
Replace
```python
                    class_name=class_name, file_get=update.default_file_get,
                )
```
with
```python
                    class_name=class_name, file_get=update.default_file_get,
                    hotfixes=Path(args.hotfixes) if args.hotfixes else None, rank_text_source=args.rank_text,
                )
```

## Done when
- `tests/test_update.py` passes (12 tests); the fast suite has no other new failures.
- Only `src/wowforever/update.py` and `src/wowforever/__main__.py` changed.
