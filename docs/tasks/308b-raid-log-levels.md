# Task #308 (offline part): raid levels in config/log_levels.toml

Make `tests/test_log_levels.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `config/log_levels.toml`. Run the test file, then the fast suite once.
- Before you start, `test_raids_are_level_60` fails.

## Why
#308: once level-60 logs exist, `validate-logs` should compare raid parses too. A location without a level is skipped,
so the six level-60 raids in `data/cache/foreverlogs/locations.txt` need one.

## Step 1: `config/log_levels.toml`
At the end of the file, add:
```toml
# Raids (#308): level-60 content, compared with the model's level-60 checkpoint once launch logs exist
"Molten Core" = 60
"Onyxia's Lair" = 60
"Blackwing Lair" = 60
"Zul'Gurub" = 60
"Ruins of Ahn'Qiraj" = 60
"Temple of Ahn'Qiraj" = 60
```

Nothing else changes.

## Done when
- `tests/test_log_levels.py` passes; no other new failures.
