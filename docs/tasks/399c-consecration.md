# Task #399 (Consecration): one-target Consecration, Divine Precision, questing takes the best alternative

Make `tests/test_ret_consecration.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit in this order: `src/wowforever/melee_scenarios.py`, `src/wowforever/classes/paladin.py`,
  `src/wowforever/classes/paladin_rotation.py`. Run the test file, then the fast suite once. Regression pins for
  any class (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, opponent kits) may move, because questing now
  takes an Output's alternatives; Claude re-derives them.
- Before you start, `tests/test_ret_consecration.py` fails.

## Why
Retribution keeps Consecration down on one target too, but it costs 565 mana per 8 s, so the Output offers the
rotation without it and the scenarios take the better one. Dungeon and raid already take the best of an Output's
alternatives (#390); questing should too. Divine Precision (+18% Holy spell hit) helps Hammer of Wrath.

## Step 1: `src/wowforever/melee_scenarios.py`
In `questing`, replace the lines from `    kill = q.mob_hp / out.dps` through
`    return 3600 / (kill + downtime + q.travel_seconds)` with:
```python
    # the best of the Output and its alternatives (a DoT, shock or Consecration dropped; #390, #399)
    return max(questing_kills_per_hour(o, q, mob_dps, eat) for o in (out, *out.alternatives))


def questing_kills_per_hour(out: Output, q, mob_dps: float, eat: float) -> float:
    """Kills per hour for one Output: kill time + recovery downtime (eating back the damage taken, unless a pet
    tanks; drinking back the mana) + travel."""
    kill = q.mob_hp / out.dps
    downtime = 0.0 if out.pet else mob_dps * kill / eat     # a pet tanks while the hunter shoots
    if out.mana_per_second > 0:
        downtime = max(downtime, out.mana_per_second * kill / q.drink_mana_per_second)
    return 3600 / (kill + downtime + q.travel_seconds)
```

## Step 2: `src/wowforever/classes/paladin.py`
1. At the end of `TALENT_EFFECTS` (directly before its closing `}`), add:
```python
    "Divine Precision": (
        EffectRule("hit_chance", r"chance to hit with Holy spells by (\d+(?:\.\d+)?)%", ("@holy_spell",)),
    ),
```
2. Delete the `UNMODELED` line `    "Divine Precision": "damage: +18% Holy spell hit",`.
3. In `output`, the line `    return Output(r.dps, r.mana_per_second, r.white_dps, r.aoe)` becomes:
```python
    out = Output(r.dps, r.mana_per_second, r.white_dps, r.aoe)
    if r.consecration_dps > 0:      # Consecration can be dropped when mana is short (#399)
        out = replace(out, alternatives=(Output(r.dps - r.consecration_dps,
                                                r.mana_per_second - r.consecration_mana_per_second,
                                                r.white_dps, r.aoe),))
    return out
```
   and add `    from dataclasses import replace` as the first import line inside `output`.

## Step 3: `src/wowforever/classes/paladin_rotation.py`
1. In the module docstring, the lines
```
Against a pack (`pack` > 1, AoE pulls #262) Consecration is kept down, hitting every mob for its base
tick damage (the melee row carries no spell power; its ticks don't roll the combat table).
```
   become
```
Consecration is kept down, on one target too (#399), hitting every mob of a pack (`pack` > 1, AoE pulls #262)
for its base tick damage plus Champion of the Light's spell power (its ticks don't roll the combat table).
```
   and in the later paragraph replace `Not modeled yet: Consecration against one mob, Exorcism` with
   `Not modeled yet: Exorcism`.
2. In `class PaladinRotation`, after the `mana_per_second` field, add:
```python
    consecration_dps: float = 0.0               # Consecration's part of dps and of mana (#399)
    consecration_mana_per_second: float = 0.0
```
3. In the Hammer of Wrath block, the line
```python
        hit = 1 - miss_chance(stats.level, stats.level + target.level_diff, stats.hit_pct) / 100
```
   becomes
```python
        hit = 1 - miss_chance(stats.level, stats.level + target.level_diff,
                              stats.hit_pct + total("hit_chance", "@holy_spell")) / 100   # Divine Precision
```
4. The Consecration block, from `    consecration = best_rank(spells, "Consecration", stats.level) if pack > 1 else None`
   through `        aoe = ("Consecration",)`, becomes:
```python
    cons_dps = cons_mana = 0.0
    consecration = best_rank(spells, "Consecration", stats.level)
    if consecration is not None and consecration.duration > 0 and consecration.periodic_damage > 0:
        period = max(consecration.duration, consecration.cooldown)
        cons_dps = ((consecration.periodic_damage + consecration.periodic_coefficient * spell_power)
                    * (1 + (all_pct + total("damage_pct", "Consecration")) / 100)
                    * pack / period)
        cons_mana = cost(consecration) / period
        holy += cons_dps
        mana += cons_mana
        used.append("Consecration")
        if pack > 1:
            aoe = ("Consecration",)
```
   (keep the `    aoe: tuple[str, ...] = ()` line that comes before it).
5. In the final `return PaladinRotation(...)` call, add
   `consecration_dps=cons_dps, consecration_mana_per_second=cons_mana` after `mana_per_second=mana - regen`.

Nothing else changes.

## Done when
- `tests/test_ret_consecration.py` passes; no other new failures apart from regression pins.
