# Task #377: warlock "Destruction spells" include Shadow Bolt

Make `tests/test_destruction_spells.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/warlock.py`. **Make the edit first**, then run the test file,
  then the fast suite once. Warlock regression pins in `tests/test_kit_stats.py` and `tests/test_dungeon_mana.py`
  may move; Claude re-derives them.
- Before you start, the 3 tests in `tests/test_destruction_spells.py` fail.

## Why
Ruin, Agonizing Flames and Cataclysm name "your Destruction spells". In WoW that means the Destruction skill line
(client SkillLineAbility, skill line 593), not the Fire school. Their rules use `("fire",)` today, so Shadow Bolt
misses them.

## Steps (`src/wowforever/classes/warlock.py`)
1. Above `TALENT_EFFECTS`, add a comment line naming the source ("client SkillLineAbility, skill line 593
   (Destruction), its damaging spells; wago 1.60.1.70425, #377") and the constant
   `DESTRUCTION_SPELLS = ("Conflagrate", "Hellfire", "Immolate", "Incinerate", "Rain of Fire", "Searing Pain",
   "Shadow Bolt", "Shadowburn", "Soul Fire")`.
2. In the `"Ruin"`, `"Agonizing Flames"` and `"Cataclysm"` rules, replace `("fire",)` with `DESTRUCTION_SPELLS`.
   Nothing else changes.

## Done when
- `tests/test_destruction_spells.py` passes (3 tests); no other new failures apart from warlock pins.
