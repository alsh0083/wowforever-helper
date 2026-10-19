# Task #397 (cat crits): Blood Frenzy's combo point and Berserk's builder crit

Make `tests/test_cat_crit_procs.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit in this order: `config/druid.toml`, `src/wowforever/classes/druid.py`,
  `src/wowforever/classes/druid_rotation.py`. Run the test file, then the fast suite once. Druid regression pins
  (opponent kits, `tests/test_kit_stats.py`) may move; Claude re-derives them.
- Before you start, the tests in `tests/test_cat_crit_procs.py` fail.

## Why
The scored Feral cat build takes Blood Frenzy 2/2 ("your non-periodic critical strikes from Cat Form abilities that
generate Combo Points have a 100% chance to add an additional Combo Point", like the rogue's Seal Fate) and Berserk
("increases the critical strike chance of your Combo Point-generating abilities by 100% ... Lasts 15 sec"). Neither
is modeled. Berserk's cooldown isn't in the client data: 180 s is a best-effort guess.

## Step 1: `config/druid.toml`
At the end of the file, add:
```toml
# Berserk (#397): +100% builder crit for 15 s (rank text); the cooldown isn't in the client data, 180 s is a
# best-effort guess (confidence LOW)
berserk = { duration = 15.0, cooldown = 180.0 }
```

## Step 2: `src/wowforever/classes/druid.py`
1. At the end of `TALENT_EFFECTS` (directly before its closing `}`), add:
```python
    "Blood Frenzy": (
        # the Cat Form part (#397); the Bear Form Rage part stays out (bear isn't scored)
        EffectRule("proc_chance", r"Combo Points have a (\d+(?:\.\d+)?)% chance to add an additional Combo Point",
                   ("@builder_crit",)),
    ),
```
2. Delete the `UNMODELED` line `    "Blood Frenzy": "resource: Rage on bear crits",`.
3. In `UNMODELED`, the line `    "Berserk": "damage: Primal Bite cleaves and crits more",` becomes
   `    "Berserk": "damage: builder crit averaged in druid_rotation (#397); Primal Bite's cleave not modeled",`.

## Step 3: `src/wowforever/classes/druid_rotation.py`
1. In the module docstring, the lines
```
duration when it gains (#397). Not modeled yet: Tiger's Fury, Berserk's cleave, Omen of Clarity,
powershifting and Shifting Power.
```
   become
```
duration when it gains (#397). Blood Frenzy's extra combo point on builder crits and Berserk's builder crit
(averaged over a guessed cooldown) count (#397). Not modeled yet: Tiger's Fury, Berserk's cleave, Omen of
Clarity, powershifting and Shifting Power.
```
2. The `from wowforever.physical import ...` line becomes:
```python
from wowforever.physical import Attacker, Target, land_chance, white_swing, yellow_attack, yellow_crit_chance
```
3. In `class CatRotation`, after the `builder: str` field, add:
```python
    builder_ev: float = 0.0                 # one builder's expected damage (#397)
    combo_points_per_builder: float = 0.0
```
4. In `cat_rotation`, the lines
```python
    builder_ev = yellow_attack(base, attacker, target, damage_pct=bleeding + total("damage_pct", builder.name),
                               crit_damage_pct=crit_damage)
    cost = max(0.0, builder.energy_cost + total("energy_cost", builder.name))
    cp_per_builder = builder.combo_points * land_chance(attacker, target)
```
   become
```python
    share = 0.0
    if taken("Berserk"):
        # Berserk (#397): +100% builder crit for its duration, averaged over its (guessed) cooldown
        share = c["berserk"]["duration"] / c["berserk"]["cooldown"]
    land = land_chance(attacker, target)
    extra_cp = total("proc_chance", "@builder_crit") / 100       # Blood Frenzy (#397)
    builder_ev = cp_per_builder = 0.0
    for weight, bonus in ((1 - share, 0.0), (share, 100.0)):
        if weight <= 0:
            continue
        builder_ev += weight * yellow_attack(base, attacker, target, crit_bonus=bonus,
                                             damage_pct=bleeding + total("damage_pct", builder.name),
                                             crit_damage_pct=crit_damage)
        cp_per_builder += weight * land * (builder.combo_points
                                           + yellow_crit_chance(attacker, target, bonus) * extra_cp)
    cost = max(0.0, builder.energy_cost + total("energy_cost", builder.name))
```
5. The final line
```python
    return CatRotation(dps=white + yellow, white_dps=white, yellow_dps=yellow, builder=builder.name)
```
   becomes
```python
    return CatRotation(dps=white + yellow, white_dps=white, yellow_dps=yellow, builder=builder.name,
                       builder_ev=builder_ev, combo_points_per_builder=cp_per_builder)
```

Nothing else changes.

## Done when
- `tests/test_cat_crit_procs.py` passes; no other new failures apart from druid pins.
