# Task #391 (part 2C): the warrior takes the better of two-hander and dual wield

Make `tests/test_fury_dual_wield.py` and `tests/test_class_engine.py` pass without breaking the rest of the fast
suite (`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/warrior.py`. Run the two test files, then the fast suite once.
  Warrior regression pins (`tests/test_kit_stats.py`, opponent kits, `tests/test_dungeon_mana.py`) may move;
  Claude re-derives them.
- Before you start, the new tests fail with `AttributeError: ... has no attribute 'dual_wield'`.

## Why
Part B gave Fury builds (main tree Fury) the dual-wield weapons. But early points of Arms leveling builds sit in
Fury, and the owner's rule is to assume the best weapons for the scenario (2026-10-17). So every warrior build runs
both weapon sets, each with its best Weaponmaster branch, and keeps the higher DPS.

## Step 1: `src/wowforever/classes/warrior.py`
1. Replace the whole `fury_stats` function with:
```python
def dual_wield(stats):
    """The same stats with the warrior_dw table's main and off hand at that level (#391)."""
    from dataclasses import replace

    from wowforever.melee_scenarios import MeleeStatTable

    dw = MeleeStatTable.load("warrior_dw").at(stats.level)
    return replace(stats, main_hand=dw.main_hand, off_hand=dw.off_hand)


def _rotation(stats, spells, cls, ranks, target, pack=1):
    """The better of the two-hander and dual wield (owner: the best weapons for the scenario, #386, #391), each
    with its best Weaponmaster branch."""
    from wowforever.classes.warrior_rotation import warrior_rotation
    from wowforever.weapon_talents import best_weapon

    runs = [best_weapon(lambda s, t: warrior_rotation(s, spells, cls, ranks, t, pack=pack), row, target, cls, ranks)[0]
            for row in (stats, dual_wield(stats))]
    return max(runs, key=lambda r: r.dps)
```
2. `output` becomes:
```python
def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None, sustained=False):
    from wowforever.melee_scenarios import Output

    r = _rotation(stats, spells, cls, ranks, target, pack)
    return Output(r.dps, 0.0, r.dps, r.aoe)
```
3. In `facts`, the line `    r = warrior_rotation(fury_stats(stats, cls, ranks), cls.spells, cls, ranks, Target(0, 0))` becomes
   `    r = _rotation(stats, cls.spells, cls, ranks, Target(0, 0))`, and remove the now unused
   `    from wowforever.classes.warrior_rotation import warrior_rotation` import inside `facts` if nothing else in it
   uses it.

Nothing else changes.

## Done when
- `tests/test_fury_dual_wield.py` and `tests/test_class_engine.py` pass; no other new failures apart from warrior
  pins.
