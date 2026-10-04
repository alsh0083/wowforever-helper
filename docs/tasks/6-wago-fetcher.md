# Task #6: wago.tools fetcher

Implement `src/wowforever/sources/wago.py` so `tests/test_source_wago.py` passes. Do not edit tests or fixtures. Tests never touch the network.

## Interface
- `TABLES: tuple[str, ...]`: Talent, TalentTab, Spell, SpellName, SpellEffect, SpellMisc, SpellLevels, SpellCastTimes, SpellPower, SpellDuration, SpellRange, SpellCooldowns, SpellTargetRestrictions, SkillLineAbility, SpellClassOptions
- `forever_builds(builds: dict, prefix: str = "1.60.") -> list[str]`: `builds` is the JSON from `https://wago.tools/api/builds` (product name → list of `{"version": ...}`). Unique versions starting with `prefix` across all products, sorted by numeric version tuple, ascending.
- `latest_build(builds: dict, prefix: str = "1.60.") -> str`
- `table_url(table: str, build: str) -> str`: `https://wago.tools/db2/{table}/csv?build={build}`
- `fetch_build(build, *, http_get, cache_dir: Path, manifest_dir: Path, tables=TABLES, delay: float = 1.0) -> Path`
  - `http_get(url) -> str` is injected; the real default lives in `wowforever.sources.http` (below)
  - writes each table to `cache_dir/<build>/<Table>.csv` (UTF-8, content exactly as received)
  - writes `manifest_dir/<build>/manifest.json`: `{"source": "wago.tools", "build", "fetched_at" (ISO UTC), "files": {Table: {"url", "sha256", "bytes"}}}`, `indent=1`, sorted keys
  - skips a table whose cached file exists and matches the manifest hash (no HTTP call); refetches a missing cache file; raises `ValueError` if a refetched file's hash differs from the manifest (data changed under the same build)
  - sleeps `delay` seconds between HTTP requests
  - returns the manifest path

Also create `src/wowforever/sources/http.py` with `http_get(url: str) -> str` using `urllib.request`, User-Agent `wowforever-helper/0.1 (personal research; github.com/alsh0083)`, 60 s timeout, raising on non-200. No tests needed for it.

Standard library only, type hints, short docstrings.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
