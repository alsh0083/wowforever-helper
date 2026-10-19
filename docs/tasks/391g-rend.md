# Task #391 (part 5): Rend and Improved Rend

Make `tests/test_rend.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/classes/warrior.py`, then `src/wowforever/classes/warrior_rotation.py`. Run
  the test file, then the fast suite once. Warrior regression pins (`tests/test_kit_stats.py`, opponent kits,
  `tests/test_dungeon_mana.py`, `tests/test_warrior_aoe.py`, `tests/test_execute.py`, `tests/test_overpower.py`,
  `tests/test_class_engine.py`) may move; Claude re-derives them.
- Before you start, the tests in `tests/test_rend.py` fail.

## Why
All four scored warrior builds take Improved Rend (+35% Rend bleed), but Rend isn't in the rotation. Rend is cheap
damage per Rage (147 over 21 s for 10 Rage), so on a single target it's kept up with the Rage left after the
cooldown abilities and Overpower, before Heroic Strike. A bleed lands or not; armor doesn't reduce it.

## Step 1: `src/wowforever/classes/warrior.py`
Add to `TALENT_EFFECTS`:
```python
    "Improved Rend": (
        EffectRule("damage_pct", r"Bleed damage done by your Rend ability by (\d+(?:\.\d+)?)%", ("Rend",)),
    ),
```
and delete the `UNMODELED` line `    "Improved Rend": "melee damage: Rend bleeds 35% harder",`.

## Step 2: `src/wowforever/classes/warrior_rotation.py`
Directly before the line `    sweeping = learned("Sweeping Strikes") if pack > 1 and taken("Sweeping Strikes") else None`
(after the Overpower block) add:
```python
    rend = learned("Rend")
    if rend is not None and rend.duration > 0 and rage > 0 and pack == 1:
        # a bleed kept up on one target (#391): it lands or not, armor doesn't touch it
        rend_rate = min(1 / rend.duration, rage / cost(rend)) if cost(rend) else 1 / rend.duration
        rend_damage = rend.periodic_damage * land_chance(attacker, target) * (1 + total("damage_pct", "Rend") / 100)
        rage -= rend_rate * cost(rend)
        yellow += rend_rate * rend_damage
        parts.append(("Rend", rend_rate * rend_damage))
        single, attacks = single + rend_rate * rend_damage, attacks + rend_rate
        used.append("Rend")
```
In the module docstring, change `Overpower follows dodges (#391).` to
`Overpower follows dodges and Rend is kept up on one target (#391).` (keep lines under 110).

Nothing else changes.

## Done when
- `tests/test_rend.py` passes; no other new failures apart from warrior pins.
