# Task #382 (part 2): the warlock rotation casts Siphon Life and Drain Life

Make `tests/test_leech_rotation.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/warlock.py`. **Make the edit first**, then run the test file,
  then the fast suite once. Warlock regression pins in `tests/test_kit_stats.py` and `tests/test_dungeon_mana.py`
  may move; Claude re-derives them.
- Before you start, 2 of the 3 tests in `tests/test_leech_rotation.py` fail; `test_siphon_life_by_hand` passes.

## Why
Siphon Life and Drain Life now carry their damage (part 1), but the warlock `ROTATION` doesn't name them, so
the caster engine never casts them. The engine already skips a spell whose teaching talent isn't taken.

## Steps (`src/wowforever/classes/warlock.py`)
In `ROTATION`:
1. `"dots": ("Corruption", "Bane of Agony", "Immolate"),` becomes
   `"dots": ("Corruption", "Bane of Agony", "Siphon Life", "Immolate"),`
2. `"fillers": ("Shadow Bolt", "Incinerate", "Searing Pain", "Wrack"),` becomes
   `"fillers": ("Shadow Bolt", "Incinerate", "Searing Pain", "Wrack", "Drain Life"),`
Nothing else changes.

## Done when
- `tests/test_leech_rotation.py` passes (3 tests); no other new failures apart from warlock pins.
