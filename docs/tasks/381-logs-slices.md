# Task #381: Forever Logs refresh by week and day

Make `tests/test_logs_slices.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests. Never run the refresh command itself:
it needs the owner's key and makes network requests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order; run the test file after steps 1 and 2, then the fast suite once.
- Before you start, every test in `tests/test_logs_slices.py` fails with an ImportError.

## Why
The statistics endpoint takes `weekNumber` (weeks from 2024-01-01; week 147 = Oct 19-25 2026) and an
undocumented `dayNumber` (1-7). The refresh always fetches the whole phase, so pre-patch logs swamp a new patch.
The API also rate-limits (HTTP 429) after about 37 quick requests.

## Step 1: `src/wowforever/sources/foreverlogs_api.py`
1. Add `from urllib.error import HTTPError` after `from urllib.parse import urlencode`.
2. After the `PER_BOSS = "stats-per-boss"` line add a blank line and
   `RETRY_SECONDS = 60.0   # wait after an HTTP 429 (rate limit) before the one retry (#381)`.
3. `statistics_url` becomes:
```python
def statistics_url(location: str, params: dict[str, str], *, week: int | None = None,
                   day: int | None = None) -> str:
    """Statistics endpoint for one location: phase 1, all difficulties, the variant's params; `week`
    (weeks from 2024-01-01) and `day` (1-7) narrow it to one slice (#381)."""
    query = {"phase": "1", "difficulty": "all", **params, "location": location}
    if week is not None:
        query["weekNumber"] = str(week)
    if day is not None:
        query["dayNumber"] = str(day)
    return f"{BASE}/statistics?{urlencode(query)}"


def slice_folder(variant: str, week: int | None, day: int | None) -> str:
    """Cache folder for one variant and slice: stats, stats-w146, stats-w147-d2 (#381)."""
    return variant + (f"-w{week}" if week is not None else "") + (f"-d{day}" if day is not None else "")


def _get_with_retry(get: Callable[[str, dict[str, str]], str], url: str, headers: dict[str, str],
                    sleep: Callable[[float], None]) -> str:
    """`get`, waiting RETRY_SECONDS and trying once more on HTTP 429 (#381)."""
    try:
        return get(url, headers)
    except HTTPError as e:
        if e.code != 429:
            raise
        sleep(RETRY_SECONDS)
        return get(url, headers)
```
4. `fetch_statistics` gains a keyword argument `slices: Sequence[tuple[int | None, int | None]] = ((None, None),)`
   after `delay: float = 2.0,`. Its docstring becomes `"""Re-fetch the statistics for every variant, slice
   (week, day) and location and write them under `cache_dir`/<slice folder>/."""`. Its loop:
```python
    for variant in variants:
        folder = cache_dir / variant
        folder.mkdir(parents=True, exist_ok=True)
        for location in locations:
            if written:
                sleep(delay)
            text = get(statistics_url(location, VARIANTS[variant]), headers)
```
   becomes
```python
    for variant in variants:
        for week, day in slices:
            folder = cache_dir / slice_folder(variant, week, day)
            folder.mkdir(parents=True, exist_ok=True)
            for location in locations:
                if written:
                    sleep(delay)
                text = _get_with_retry(get, statistics_url(location, VARIANTS[variant], week=week, day=day),
                                       headers, sleep)
```
   and the four lines after it (the `success` check, `path = ...`, `path.write_text(...)`, `written.append(path)`)
   move one level deeper, unchanged.
5. In `fetch_boss_statistics`, `text = get(boss_statistics_url(location, boss_id), headers)` becomes
   `text = _get_with_retry(get, boss_statistics_url(location, boss_id), headers, sleep)`.

## Step 2: `src/wowforever/validate.py`
1. Add this function directly before `def log_averages(`:
```python
def _stat_files(stats_dirs: Path | Iterable[Path]) -> list[Path]:
    """The JSON files of one statistics folder, or of several (week and day slices, #381)."""
    dirs = [stats_dirs] if isinstance(stats_dirs, Path) else list(stats_dirs)
    return [path for d in dirs for path in sorted(d.glob("*.json"))]
```
2. In both `log_averages` and `log_percentiles`: the parameter `stats_dir: Path = STATS_DIR` becomes
   `stats_dir: Path | Iterable[Path] = STATS_DIR`, and `for path in sorted(stats_dir.glob("*.json")):` becomes
   `for path in _stat_files(stats_dir):`.

## Step 3: `src/wowforever/__main__.py`
1. After the `vl.add_argument("--single-target", ...)` call add:
```python
    vl.add_argument("--stats", action="append", help="statistics folder(s) under data/cache/foreverlogs/ to compare "
                    "with instead of the default (repeatable; week and day slices add up by parses, #381)")
```
2. After the `fl.add_argument("--delay", ...)` line add:
```python
    fl.add_argument("--week", type=int, action="append",
                    help="fetch only this week (weeks from 2024-01-01; 147 = Oct 19-25 2026), into <variant>-w<N>/ (repeatable)")
    fl.add_argument("--day", type=int, action="append", choices=range(1, 8),
                    help="with --week: only this day of the week (1-7), into <variant>-w<N>-d<D>/ (repeatable)")
```
3. In the `validate-logs` branch, directly before the line `        print(markdown(compare(reports, log_averages(stats, boss_ids=boss_ids),`
   add:
```python
        if args.stats:
            stats = [STATS_DIR.parent / name for name in args.stats]
```
4. In the `foreverlogs-refresh` branch, directly after `variants = args.variant or list(foreverlogs_api.VARIANTS)` add:
```python
        if args.day and not args.week:
            print("--day needs --week")
            return 1
        slices = [(w, d) for w in args.week for d in (args.day or [None])] if args.week else [(None, None)]
```
   and in the `foreverlogs_api.fetch_statistics(...)` call add `slices=slices,` after `delay=args.delay,`.

## Step 4: `docs/patch-update.md`
In "## 5. Keep checking while the meta settles", add a blank line and this paragraph after the existing paragraph (before "## 6. Move the model"):
```
After a patch, fetch only post-patch logs: `.venv/Scripts/python -m wowforever foreverlogs-refresh --week 147`
(weeks from 2024-01-01; add `--day 1 --day 2` for single days), then compare with
`validate-logs --stats stats-w147` (repeat `--stats` to add slices up). A 429 waits 60 s and retries once.
```

Nothing else changes.

## Done when
- `tests/test_logs_slices.py` passes (7 tests); the fast suite has no new failures.
