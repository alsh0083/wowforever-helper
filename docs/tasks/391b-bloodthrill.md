# Task #391 (Bloodthrill): Overpower activations from main-hand hits on the Rend target

Make `tests/test_bloodthrill.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/classes/warrior.py`, then `src/wowforever/classes/warrior_rotation.py`. Run
  the test file, then the fast suite once. Warrior regression pins (`tests/test_dungeon_mana.py`,
  `tests/test_kit_stats.py`, opponent kits) may move; Claude re-derives them.
- Before you start, the tests in `tests/test_bloodthrill.py` fail.

## Why
Bloodthrill (Arms, 5/5 in the scored Arms build): "Grants your Main Hand melee attacks against enemies afflicted by
your Rend a 20% chance to allow an activation of Overpower." The rotation keeps Rend up on one target, so each
landed main-hand swing adds that chance to Overpower's activations.

## Step 1: `src/wowforever/classes/warrior.py`
1. At the end of `TALENT_EFFECTS` (directly before its closing `}`), add:
```python
    "Bloodthrill": (
        EffectRule("proc_chance", r"a (\d+(?:\.\d+)?)% chance to allow an activation of Overpower", ("@bloodthrill",)),
    ),
```
2. Delete the `UNMODELED` line `    "Bloodthrill": "proc: main-hand hits on Rend targets can enable an ability",`.

## Step 2: `src/wowforever/classes/warrior_rotation.py`
1. The `from wowforever.physical import ...` line becomes (adding `white_land_chance`):
```python
from wowforever.physical import (Attacker, Target, land_chance, white_land_chance, white_swing, yellow_attack,
                                 yellow_crit_chance)
```
2. `overpower_rate` becomes:
```python
def overpower_rate(attacks: float, dodge: float, cooldown: float, rage: float, cost: float,
                   extra: float = 0.0) -> float:
    """Overpowers per second (#391): one per dodged attack plus `extra` activations per second (Bloodthrill), at
    most one per cooldown, as Rage allows."""
    rate = min(attacks * dodge + extra, 1 / cooldown if cooldown > 0 else float("inf"))
    return min(rate, rage / cost) if cost > 0 else rate
```
3. In `warrior_rotation`, the line
```python
        op_rate = overpower_rate(attacks, dodge, overpower.cooldown, rage, cost(overpower))
```
   becomes
```python
        extra = 0.0
        rend_kept = learned("Rend")
        if rend_kept is not None and rend_kept.duration > 0 and pack == 1:
            # Bloodthrill (#391): landed main-hand swings on the Rend target can enable Overpower
            extra = (swings * white_land_chance(attacker, target, dual_wield=off is not None)
                     * total("proc_chance", "@bloodthrill") / 100)
        op_rate = overpower_rate(attacks, dodge, overpower.cooldown, rage, cost(overpower), extra)
```

Nothing else changes.

## Done when
- `tests/test_bloodthrill.py` passes; no other new failures apart from warrior pins.
