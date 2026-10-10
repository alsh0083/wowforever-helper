# Task #172: levels for City of Dalaran and The Stockade

Make `tests/test_log_levels.py` pass without breaking the rest of the suite. Edit `config/log_levels.toml` only. Do not edit the tests.

## Why
`validate-logs` compares each dungeon's Forever Logs parses with the model at that dungeon's level, and skips any dungeon missing from `config/log_levels.toml`. After the Oct 10 refresh, City of Dalaran (201 parses, new in the Oct 8 patch) and The Stockade (35 parses) have parses but no level.

## Change
Add these two lines to `config/log_levels.toml`, keeping the file's order by level and its comment style:
```
"The Stockade" = 25                # Classic 22-30, as Shadowfang Keep
"City of Dalaran" = 29             # Forever: 28-33 (theforeverera.com, wowforeverguides.com); beta cap 30
```
Put `The Stockade` right after `Shadowfang Keep`, and `City of Dalaran` right after `Scarlet Monastery - Graveyard`. Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_log_levels.py` fails with `KeyError: 'City of Dalaran'`. That's the expected failure. Install nothing and ask for no elevation. Write the edit with `tools/apply_patch.py` (see AGENTS.md). Check with `.venv/Scripts/python -m pytest tests/test_log_levels.py tests/test_validate.py`. Don't run the full suite.

## Done when
`.venv/Scripts/python -m pytest tests/test_log_levels.py tests/test_validate.py` passes.
