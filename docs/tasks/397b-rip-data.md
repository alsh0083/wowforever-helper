# Task #397 (part 2A): Rip's periodic damage per combo point in the spell data

Make `tests/test_rip_data.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do steps 1-3, then run the tool in step 3 exactly once, then the test file and the fast suite.
- Before you start, the tests in `tests/test_rip_data.py` fail.

## Why
Rip's damage grows per combo point on its periodic aura (EffectPointsPerResource 25.5 per tick); the spell data
only reads per-combo-point damage from direct damage effects.

## Step 1: `src/wowforever/schema.py`
In `class SpellRank`, directly after the `per_combo_point: float = 0.0 ...` line add
`    periodic_per_combo_point: float = 0.0   # extra periodic damage per combo point, over the duration (Rip, #397)`

## Step 2: `src/wowforever/normalize_spells.py`
1. The line `    periodic_damage = periodic_coefficient = tick_period = 0.0` becomes
   `    periodic_damage = periodic_coefficient = tick_period = periodic_per_combo_point = 0.0`
2. Directly after `        periodic_coefficient = _f(dot["EffectBonusCoefficient"]) * ticks` (the one inside
   `if dot is not None:`) add
   `        periodic_per_combo_point = _f(dot["EffectPointsPerResource"]) * ticks`
3. In the `SpellRank(...)` call, add `periodic_per_combo_point=periodic_per_combo_point,` right after
   `per_combo_point=per_combo_point,`.

## Step 3: `tools/refresh_periodic.py`, then run it
`FIELDS = ("periodic_damage", "periodic_coefficient", "tick_period", "ranged_attack_power")` becomes
`FIELDS = ("periodic_damage", "periodic_coefficient", "tick_period", "ranged_attack_power", "periodic_per_combo_point")`
(split over two lines if it passes 110 characters), and add `#397 adds periodic_per_combo_point (Rip).` as a new
line after the `#388 adds ...` docstring line. Then run `.venv/Scripts/python tools/refresh_periodic.py 1.60.1.70425`
once; it prints the Rip ranks (and any other DoT with a per-combo-point aura).

Nothing else changes.

## Done when
- `tests/test_rip_data.py` passes; `git diff data/datasets` only adds `periodic_per_combo_point` lines; the fast suite
  has no new failures.
