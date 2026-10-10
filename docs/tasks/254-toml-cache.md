# Task #254: parse each config TOML once

Make `tests/test_toml_cache.py` pass without breaking the rest of the suite. Do not edit the tests.

## Why
Building one class report re-reads and re-parses `config/*.toml` about 218,000 times (cProfile, rogue: 260 of 325 seconds). Every rotation and scenario call does `tomllib.loads(CONFIG.read_text(encoding="utf-8"))`.

## Change
1. **Create `src/wowforever/toml_cache.py`:**
   ```python
   """Parsed config TOML, cached per file version (#254)."""

   import copy
   import tomllib
   from pathlib import Path
   from typing import Any

   _CACHE: dict[Path, tuple[tuple[int, int], dict[str, Any]]] = {}


   def load_toml(path: Path) -> dict[str, Any]:
       """`path` parsed as TOML: parsed again only when its mtime or size changes; each caller gets a deep copy."""
       path = Path(path).resolve()
       st = path.stat()
       version = (st.st_mtime_ns, st.st_size)
       hit = _CACHE.get(path)
       if hit is None or hit[0] != version:
           hit = (version, tomllib.loads(path.read_text(encoding="utf-8")))
           _CACHE[path] = hit
       return copy.deepcopy(hit[1])


   def clear() -> None:
       """Forget every cached file."""
       _CACHE.clear()
   ```
   Keep the `tomllib.loads` call written exactly that way: the test counts parses by replacing `toml_cache.tomllib.loads`.

2. **In each of these files, replace every `tomllib.loads(X.read_text(encoding="utf-8"))` with `load_toml(X)`**, keeping any indexing after it (for example `tomllib.loads(CONFIG.read_text(encoding="utf-8"))[class_name]` becomes `load_toml(CONFIG)[class_name]`):
   - `src/wowforever/melee_stats.py`
   - `src/wowforever/melee_scenarios.py`
   - `src/wowforever/scenarios.py`
   - `src/wowforever/group.py`
   - `src/wowforever/gear.py` (both places)
   - `src/wowforever/classes/druid_rotation.py`, `hunter_rotation.py` (both lines), `paladin_rotation.py`, `rogue_rotation.py`, `shaman_rotation.py`, `warrior_rotation.py` (both functions)
   - `src/wowforever/pvp/class_pvp.py`
   - `src/wowforever/pvp/kit_stats.py`

   Add `from wowforever.toml_cache import load_toml` to each one's imports, and remove `import tomllib` from any file that no longer uses it. Change nothing else: no other files, no logic changes.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_toml_cache.py` fails with `ModuleNotFoundError: No module named 'wowforever.toml_cache'`. That's the expected failure. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md). Edit `toml_cache.py` first, then the files in the order listed. Don't run the full suite: it takes minutes. Teardown errors about removing `.pytest-tmp` directories are a sandbox artifact: ignore them.

## Done when
`.venv/Scripts/python -m pytest tests/test_toml_cache.py -m "not slow"` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"` (about 20 seconds).
