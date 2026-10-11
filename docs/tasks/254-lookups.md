# Task #254 step 2: index talent lookups, memoize talent aliases and spell scaling

Make `tests/test_lookups.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/schema.py` and `src/wowforever/scenarios.py`.

## Why
Profiling the mage report: `ClassData.talent` scans the talent tuple 23 million times, `talent_aliases` re-reads `config/talent_renames.toml` on every call (56 s), and `scaled()` rebuilds the same `SpellRank` 1.5 million times (32 s).

## Change
1. **`src/wowforever/schema.py`, `talent_aliases`:** move the body into a memoized helper, keeping the result identical:
   ```python
   @functools.lru_cache(maxsize=None)
   def _aliases(name: str, renames_file: Path) -> frozenset[str]:
       """Lowercased `name` plus every name config/talent_renames.toml renames it from or to."""
       renames = load_toml(renames_file) if renames_file.exists() else {}
       ...same loop as today, on `name` (already lowercased)...


   def talent_aliases(name: str) -> set[str]:
       """`name` and every name a patch renamed it from or to (config/talent_renames.toml), lowercased."""
       return set(_aliases(name.lower(), RENAMES_FILE))
   ```
   Import `functools` at the top, and `load_toml` from `wowforever.toml_cache`. Drop the function-level `import tomllib`.

2. **`src/wowforever/schema.py`, `ClassData`:** add two `functools.cached_property` indexes, and use them in `talent` and `talent_named`:
   ```python
   @functools.cached_property
   def _talents_by_id(self) -> dict[int, Talent]:
       return {t.talent_id: t for t in self.talents}

   @functools.cached_property
   def _talents_by_name(self) -> dict[str, list[Talent]]:
       out: dict[str, list[Talent]] = {}
       for t in self.talents:
           out.setdefault(t.name.lower(), []).append(t)
       return out
   ```
   - `talent(talent_id)` returns `self._talents_by_id[talent_id]`, still raising `KeyError(talent_id)` when the id is missing.
   - `talent_named(name)` collects `[t for alias in talent_aliases(name) for t in self._talents_by_name.get(alias, [])]`, then keeps today's check: exactly one match, otherwise `KeyError(f"{name!r}: {len(matches)} matches")`.
   `ClassData` is a frozen dataclass without slots, so `cached_property` works on it. Change no fields.

3. **`src/wowforever/scenarios.py`, `scaled`:** decorate with `@functools.lru_cache(maxsize=None)` (import `functools`). Leave its body unchanged.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_lookups.py` fails with `AttributeError: module 'wowforever.schema' has no attribute '_aliases'`, among other errors. That's the expected failure. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md). Do `schema.py` first, then `scenarios.py`. Teardown errors about removing `.pytest-tmp` directories are a sandbox artifact: ignore them.

## Done when
`.venv/Scripts/python -m pytest tests/test_lookups.py tests/test_builds.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"` (about 20 seconds).
