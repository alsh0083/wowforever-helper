# Task #10: trainable spell ranks

Implement `src/wowforever/normalize_spells.py` so `tests/test_spells.py` passes. Do not edit tests, fixtures or `schema.py`. Uses `read_tables` from `wowforever.normalize`.

## Interface
- `class_spells(tables, *, skill_lines: Sequence[int]) -> tuple[SpellRank, ...]`: every trainable spell rank of the class, sorted by (name, rank).
- `ranks_of(spells, name) -> list[SpellRank]`: the ranks with that name, in rank order.

## Which spells
- `SkillLineAbility` rows whose `SkillLine` is in `skill_lines`, **excluding** `AcquireMethod == 3` (Season of Discovery runes) and spells whose `SpellLevels.BaseLevel` is 0 or missing.
- Name from `SpellName`. **Rank** = position among same-named spells sorted by (BaseLevel, spell ID), starting at 1.

## Fields (one row per spell; `DifficultyID` 0 rows only)
| SpellRank field | Source |
|---|---|
| `level` | `SpellLevels.BaseLevel` |
| `scaling_max_level` | `SpellLevels.MaxLevel` when the damage effect has `EffectRealPointsPerLevel` > 0, else 0 |
| `schools` | `SpellMisc.SchoolMask` bits, in this order: 1 physical, 2 holy, 4 fire, 8 nature, 16 frost, 32 shadow, 64 arcane |
| `cast_time` | `SpellCastTimes.Base` (ms → s) via `SpellMisc.CastingTimeIndex` |
| `duration` | `SpellDuration.Duration` (ms → s) via `SpellMisc.DurationIndex`; 0 if no row |
| `range` | `SpellRange.RangeMax_0` via `SpellMisc.RangeIndex` |
| `mana_cost` | `SpellPower.ManaCost` where `PowerType == 0` (int) |
| `cooldown` | max(`RecoveryTime`, `CategoryRecoveryTime`) from `SpellCooldowns` (ms → s) |
| `max_targets` | `SpellTargetRestrictions.MaxTargets` (0 if no row) |
| `min_damage`, `max_damage` | first `SpellEffect` with `Effect == 2` (school damage): `bp * (1 - var/2)`, `bp * (1 + var/2)` with `bp = EffectBasePointsF`, `var = Variance` |
| `coefficient` | that effect's `EffectBonusCoefficient` |
| `damage_per_level` | that effect's `EffectRealPointsPerLevel` |
| `slow_pct` | `-EffectBasePointsF` of an effect with `Effect == 6` and `EffectAura == 33` |
| periodic (DoT) | an effect with `Effect == 6`, `EffectAura == 3`: `tick_period = EffectAuraPeriod/1000`, ticks = `duration // tick_period`, `periodic_damage = EffectBasePointsF * ticks`, `periodic_coefficient = EffectBonusCoefficient * ticks` |
| periodic (area) | spell has an `Effect == 179` (area trigger) and an `Effect == 6`, `EffectAura == 226` effect: `tick_period` from that effect's `EffectAuraPeriod`. Tick damage comes from the **tick spell**: a spell **not** in `SkillLineAbility` with the same name and the same `BaseLevel`, and an `Effect == 2` row. `periodic_damage = tick bp * ticks`, `periodic_coefficient = tick coefficient * ticks`. No tick spell → no periodic part. |

Floats unrounded; tests compare approximately. Standard library only, type hints, short docstrings.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
