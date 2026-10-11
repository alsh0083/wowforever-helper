# Task #172: refresh the cached Forever Logs statistics with one command

Make `tests/test_foreverlogs_api.py` pass without breaking the rest of the suite. Create `src/wowforever/sources/foreverlogs_api.py`, and edit `src/wowforever/sources/http.py` and `src/wowforever/__main__.py`. Do not edit the tests. Do not touch `src/wowforever/sources/foreverlogs.py` (that module reads browser HAR files and never fetches).

## Why
`validate-logs` and `group-buffs` read Forever Logs statistics cached under `data/cache/foreverlogs/` (gitignored), one JSON response per location in four folders. They were fetched by hand. A new game build needs a refresh, so it should be one command.

## 1. `src/wowforever/sources/foreverlogs_api.py` (standard library only)
- `BASE = "https://foreverlogs.gg/api/public/v1"`
- `VARIANTS: dict[str, dict[str, str]]`, exactly as the test lists: the extra query parameters of each cache folder.
- `cache_name(location: str) -> str`: replace every character that isn't a letter, digit or `-` with `_`.
- `statistics_url(location: str, params: dict[str, str]) -> str`: `BASE + "/statistics?" + urlencode(...)` with `phase=1`, `difficulty=all`, then `params`, then `location`.
- `fetch_statistics(cache_dir: Path, api_key: str, *, variants: Sequence[str], locations: Sequence[str], get: Callable[[str, dict[str, str]], str], sleep: Callable[[float], None] = time.sleep, delay: float = 2.0) -> list[Path]`:
  - Check every name in `variants` is in `VARIANTS` before any request; otherwise raise `ValueError` naming the unknown variant.
  - For each variant, then each location (in the given order): call `get(url, {"Authorization": f"Bearer {api_key}"})`, parse the JSON, and raise `ValueError` naming the location and variant if `success` isn't `True`. Otherwise write the response text unchanged (UTF-8, `newline="\n"`) to `cache_dir / variant / f"{cache_name(location)}.json"`, creating the folder.
  - Call `sleep(delay)` between requests, not before the first one.
  - Return the written paths in order.
- `read_api_key(environ: Mapping[str, str], dotenv: Path) -> str`: `environ["FOREVERLOGS_API_KEY"]` if set and non-empty; else the `FOREVERLOGS_API_KEY=` line of `dotenv` (strip whitespace and one pair of surrounding `"` or `'` quotes); else raise `ValueError` mentioning `FOREVERLOGS_API_KEY`. Never print or log the key.

## 2. `src/wowforever/sources/http.py`
Add `http_get_with_headers(url: str, headers: Mapping[str, str]) -> str`, like `http_get` but sending `headers` in addition to the `User-Agent`. Make `http_get_bytes` share the code rather than duplicating it.

## 3. `src/wowforever/__main__.py`
New subcommand `foreverlogs-refresh`, following the pattern of the others:
- `--variant` (repeatable; default: all four `VARIANTS` keys), `--delay` (float, default 2.0).
- Locations come from `data/cache/foreverlogs/locations.txt`, one per line, skipping blank lines.
- Key from `read_api_key(os.environ, Path(".env"))`.
- Calls `fetch_statistics(Path("data/cache/foreverlogs"), key, ..., get=http_get_with_headers)` and prints `wrote N files` plus one line per variant with its file count. Returns 0.
- Help text: `refresh the cached Forever Logs statistics (#172); about 37 requests per variant, owner's key`.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_foreverlogs_api.py` fails at collection with `ModuleNotFoundError: wowforever.sources.foreverlogs_api`. That's the expected failure. Install nothing and ask for no elevation. There is no network: never call the real API, and don't run the new command. Write edits with `tools/apply_patch.py` (see AGENTS.md). Start with `foreverlogs_api.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_foreverlogs_api.py tests/test_validate.py`. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest tests/test_foreverlogs_api.py` passes, and `.venv/Scripts/python -m wowforever foreverlogs-refresh --help` prints the help.
