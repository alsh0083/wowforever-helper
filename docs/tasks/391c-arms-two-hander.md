# Task #391 (weapon sets): only Fury dual wields; Arms keeps the two-hander

Make `tests/test_fury_dual_wield.py` and `tests/test_class_engine.py` pass without breaking the rest of the fast
suite (`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/warrior.py`. Run the two test files, then the fast suite once.
  Warrior regression pins (`tests/test_dungeon_mana.py` warrior-arms, `tests/test_kit_stats.py`, opponent kits)
  may move; Claude re-derives them.
- Before you start, `test_output_takes_the_better_weapon_set[warrior-arms-1]` and the warrior cases of
  `test_output_wraps_the_class_rotation` fail.

## Why
Owner (2026-10-18): "assume 2hander for arms unless meta shifts later". Every warrior build currently takes the
better of a two-hander and dual wield, so Arms scores as a dual wielder. Only a build whose main tree (most points)
is Fury should consider dual wield.

## Step 1: `src/wowforever/classes/warrior.py`
`_rotation` becomes:
```python
def _rotation(stats, spells, cls, ranks, target, pack=1):
    """The better of the two-hander and dual wield for a Fury build (owner: the best weapons for the scenario,
    #386, #391); other builds keep the two-hander (owner, 2026-10-18). Each with its best Weaponmaster branch."""
    from wowforever.classes.warrior_rotation import warrior_rotation
    from wowforever.melee_scenarios import main_tree
    from wowforever.weapon_talents import best_weapon

    rows = (stats, dual_wield(stats)) if main_tree(cls, ranks) == "Fury" else (stats,)
    runs = [best_weapon(lambda s, t: warrior_rotation(s, spells, cls, ranks, t, pack=pack), row, target, cls, ranks)[0]
            for row in rows]
    return max(runs, key=lambda r: r.dps)
```

Nothing else changes.

## Done when
- Both test files pass; no other new failures apart from warrior pins.
