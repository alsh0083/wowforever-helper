# Task #386: Weaponmaster and Hack and Slash take the best weapon for each scenario

Make `tests/test_weapon_talents.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. **Create `src/wowforever/weapon_talents.py` first** (step 1), then run the test file, then
  steps 2-3, then the fast suite once. Warrior and rogue regression pins (`tests/test_kit_stats.py`,
  `tests/test_dungeon_mana.py`, opponent kits) may move; Claude re-derives them.
- Before you start, every test in `tests/test_weapon_talents.py` fails with an ImportError.

## Why
Both talents give a bonus that depends on the weapon type, and the stat tables carry no weapon type. Owner
decision (2026-10-17): assume the best weapon for the given scenario, so each fight takes the branch that
gives the most DPS.

## Step 1: create `src/wowforever/weapon_talents.py` with exactly this content

```python
"""Weapon-type talents (#386): Weaponmaster (warrior) and Hack and Slash (rogue) give a bonus that
depends on the weapon. The stat tables carry no weapon type, so each scenario takes the branch with the
most DPS (owner decision 2026-10-17): the best weapon for that fight.

Per rank: +1% crit, ignore 3% of the target's armor, or a 1% chance on a landed attack of an extra
attack. Best effort: an extra attack counts as an average attack, so it adds its chance times the
rotation's DPS, all of it white damage.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any

from wowforever.physical import Target
from wowforever.schema import ClassData

BRANCHES = {
    "Weaponmaster": {"axe": "crit", "mace": "armor", "sword": "extra"},
    "Hack and Slash": {"dagger": "crit", "mace": "armor", "sword": "extra"},
}
PER_RANK = {"crit": 1.0, "armor": 3.0, "extra": 1.0}


def best_weapon(run: Callable[[Any, Target], Any], stats: Any, target: Target, cls: ClassData,
                ranks: Mapping[int, int]) -> tuple[Any, str | None]:
    """(result, weapon) with the most DPS, where `run(stats, target)` returns a rotation result with
    `dps` and `white_dps`; weapon is None when the build takes no weapon-type talent."""
    taken = [(t.name, ranks[t.talent_id]) for t in cls.talents
             if t.name in BRANCHES and ranks.get(t.talent_id, 0) > 0]
    if not taken:
        return run(stats, target), None
    name, rank = taken[0]
    best = None
    for weapon, kind in BRANCHES[name].items():
        value = PER_RANK[kind] * rank
        if kind == "crit":
            r = run(replace(stats, crit_pct=stats.crit_pct + value), target)
        elif kind == "armor":
            r = run(stats, replace(target, armor=target.armor * (1 - value / 100)))
        else:
            r = run(stats, target)
            extra = r.dps * value / 100
            r = replace(r, dps=r.dps + extra, white_dps=r.white_dps + extra)
        if best is None or r.dps > best[0].dps:
            best = (r, weapon)
    return best
```

## Step 2: `src/wowforever/classes/warrior.py`
1. In `UNMODELED`, the line
   `    "Weaponmaster": "melee damage: weapon-type bonus (crit, damage)",`
   becomes
   `    "Weaponmaster": "melee damage: weapon-type bonus, best branch per scenario (weapon_talents.py, #386)",`
2. In `output`, the line
   `    r = warrior_rotation(stats, spells, cls, ranks, target, pack=pack)`
   becomes these two lines:
   ```python
       r, _ = best_weapon(lambda s, t: warrior_rotation(s, spells, cls, ranks, t, pack=pack),
                          stats, target, cls, ranks)
   ```
   and add `    from wowforever.weapon_talents import best_weapon` after the other two imports in `output`.

## Step 3: `src/wowforever/classes/rogue.py`
1. In `UNMODELED`, the line
   `    "Hack and Slash": "proc: weapon-based extra attack chance",`
   becomes
   `    "Hack and Slash": "melee damage: weapon-type bonus, best branch per scenario (weapon_talents.py, #386)",`
2. In `output`, the line
   `    r = rogue_rotation(stats, spells, cls, ranks, target, pack=pack)`
   becomes
   ```python
       r, _ = best_weapon(lambda s, t: rogue_rotation(s, spells, cls, ranks, t, pack=pack),
                          stats, target, cls, ranks)
   ```
   and add `    from wowforever.weapon_talents import best_weapon` after the other two imports in `output`.

Nothing else changes.

## Done when
- `tests/test_weapon_talents.py` passes (7 tests); no other new failures apart from warrior and rogue pins.
