# Task #250: a `slow` marker for the full-report tests

Make `tests/test_markers.py` pass without breaking the rest of the suite. Do not edit `tests/test_markers.py`.

## Why
Four tests that build whole class reports take 605 of the suite's 624 seconds. A `slow` marker lets the quick loop skip them with `pytest -m "not slow"`.

## Change
Three files, nothing else:

1. `pyproject.toml`: under `[tool.pytest.ini_options]`, add
   ```toml
   markers = ["slow: builds whole class reports (minutes); skip with -m \"not slow\""]
   ```
2. `tests/test_report.py`: after the imports, add a module-level `pytestmark = pytest.mark.slow` (the module already imports `pytest`).
3. `tests/test_melee_report.py`: the same `pytestmark = pytest.mark.slow` after its imports. Add `import pytest` only if it's missing.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_markers.py` fails with `KeyError: 'markers'`. That's the expected failure. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md). Do not run the full suite or `tests/test_report.py` / `tests/test_melee_report.py`: they take minutes. Teardown errors about removing `.pytest-tmp` directories are a sandbox artifact: ignore them.

## Done when
`.venv/Scripts/python -m pytest tests/test_markers.py` passes.
