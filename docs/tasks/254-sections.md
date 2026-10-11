# Task #254 step 3: copy only the config section a caller needs, and cache the assumption and consensus loaders

Make `tests/test_toml_cache.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only the four files named below.

## Why
After steps 1 and 2, the priest report spends 47 s deep-copying cached config: `gear.caster_config` alone calls `load_toml` 153,000 times and copies the whole `casters.toml` each time, though it only needs one class's table. `Assumptions.load` (45,000 calls) and `Consensus.load` (8,000 calls) still parse their TOML on every call.

## Change
1. **`src/wowforever/toml_cache.py`:** add, below `load_toml`:
   ```python
   def load_section(path: Path, key: str) -> Any:
       """A deep copy of the top-level table `key` of `path` (KeyError when missing), without copying the rest."""
       path = Path(path)
       parsed = _CACHE.get(path)
       if parsed is None:
           parsed = _CACHE[path] = tomllib.loads(path.read_text(encoding="utf-8"))
       return copy.deepcopy(parsed[key])
   ```
   Then make `load_toml` use the same lookup. Factor the three lookup lines into a private `_parsed(path)` that both call, and keep the `tomllib.loads` call written exactly that way.
2. **`src/wowforever/gear.py`, `caster_config`:** `return load_section(CASTERS, class_name)` instead of `load_toml(CASTERS)[class_name]`. Import `load_section` next to `load_toml`.
3. **`src/wowforever/melee_stats.py`, `class_config`:** `return load_section(CONFIG, class_name)`. Import `load_section`. If `load_toml` is no longer used in the file, import only `load_section`.
4. **`src/wowforever/assumptions.py` and `src/wowforever/consensus.py`, the `load` classmethods:** `raw = load_toml(path)` instead of `raw = tomllib.loads(path.read_text(encoding="utf-8"))`. Import `from wowforever.toml_cache import load_toml`, and remove `import tomllib` if nothing else in the file uses it.

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, the new tests in `tests/test_toml_cache.py` fail: `load_section` doesn't exist yet, and the two loaders still parse every time. That's the expected failure. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above. Teardown errors about removing `.pytest-tmp` directories are a sandbox artifact: ignore them.

## Done when
`.venv/Scripts/python -m pytest tests/test_toml_cache.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"` (about 10 seconds).
