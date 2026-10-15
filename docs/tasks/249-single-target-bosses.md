# Task #249: per-boss Forever Logs statistics and a single-target comparison

Make `tests/test_foreverlogs_api.py` and `tests/test_validate.py` pass without breaking the rest of the suite. Edit only `src/wowforever/sources/foreverlogs_api.py`, `src/wowforever/validate.py` and `src/wowforever/__main__.py`. Do not edit the tests or `config/single_target_bosses.toml`.

## Why
`validate-logs --boss-only` still counts bosses with adds and cleave, but the model scores one target. Per-boss statistics for a hand-picked list of single-target bosses (`config/single_target_bosses.toml`, empty until launch) give a cleaner comparison.

## 1. `foreverlogs_api.py`
- `PER_BOSS = "stats-per-boss"`, a module constant. Do **not** add it to `VARIANTS`.
- `boss_statistics_url(location: str, boss_id: int) -> str`: `statistics_url(location, {**VARIANTS["stats-boss-only"], "bossId": str(boss_id)})`.
- `fetch_boss_statistics(cache_dir: Path, api_key: str, *, bosses: Sequence[tuple[str, int]], get, sleep=time.sleep, delay: float = 2.0) -> list[Path]`: same shape as `fetch_statistics`. It takes one request per `(location, boss_id)` with `boss_statistics_url` and writes `cache_dir / PER_BOSS / f"{boss_id}.json"`. It sleeps `delay` between requests (not before the first) and sends the same Authorization header. On `success` not true, raise `ValueError` naming the boss id, before writing.
- `read_boss_list(path: Path) -> list[tuple[str, int]]`: `tomllib` the file and return `[(b["location"], b["id"]) for b in data.get("bosses", [])]`.

## 2. `validate.py`
`log_averages` and `log_percentiles` gain a last keyword parameter `boss_ids: Collection[int] | None = None`. When it is not `None`, skip a file whose `body.get("boss_id")` is not in `boss_ids`. Put the check next to the existing `level is None` skip in both functions. Nothing else changes.

## 3. `__main__.py`
- `validate-logs` gains `--single-target` (store_true, help: "compare with the single-target bosses in config/single_target_bosses.toml only (data/cache/foreverlogs/stats-per-boss/)"). With it, `stats = STATS_DIR.parent / "stats-per-boss"` and `boss_ids = {b for _, b in read_boss_list(Path("config/single_target_bosses.toml"))}`, passed to both `log_averages` and `log_percentiles`. If the list is empty, print `config/single_target_bosses.toml lists no bosses` and return 1.
- `foreverlogs-refresh`: if `foreverlogs_api.PER_BOSS` is among `args.variant`, read the list the same way. If it's empty, print the same message and return 1 **before** reading the API key. Otherwise call `fetch_boss_statistics(cache, key, bosses=..., get=http_get_with_headers, delay=args.delay)`. The other requested variants go through `fetch_statistics` as now. The default (no `--variant`) stays the four `VARIANTS` only. Update the `--variant` help to mention `stats-per-boss` (one request per listed boss, not in the default).

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_foreverlogs_api.py` fails with `ImportError` on `PER_BOSS`, and `tests/test_validate.py::test_single_target_filter_keeps_only_the_listed_bosses` fails with `TypeError` on `boss_ids`. Those are the expected failures; implementing the above is the task. Install nothing, make no network calls, and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Start with `foreverlogs_api.py`, then `validate.py`, then `__main__.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_foreverlogs_api.py tests/test_validate.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
