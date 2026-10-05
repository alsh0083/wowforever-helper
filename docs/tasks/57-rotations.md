# Task #57: rotations and proc/stack talents (mage)

Make `tests/test_rotation.py` pass without breaking other tests. Do not edit tests or fixtures. Standard library only, type hints, short docstrings.

## 1. Arcane Missiles damage (`src/wowforever/normalize_spells.py`)
Arcane Missiles is channeled; its effect with `Effect == 6`, `EffectAura == 23` (periodic trigger) fires `EffectTriggerSpell` every `EffectAuraPeriod` ms. The triggered spell's `Effect == 2` row holds the per-missile damage. For such spells: `tick_period = period / 1000`, ticks = `duration // tick_period`, `periodic_damage = missile bp * ticks`, `periodic_coefficient = missile coefficient * ticks`. Add `AURA_PERIODIC_TRIGGER = 23`. Index trigger spells' effects even though they aren't in SkillLineAbility.

## 2. Talent rules (`src/wowforever/classes/mage.py`)
Add to `TALENT_EFFECTS` (and remove from `UNMODELED`):
| Talent | kind | applies_to | value per rank |
|---|---|---|---|
| Winter's Chill | `crit_chance` | `("Frostbolt", "Ice Lance", "@sustained")` | 2% × the "Stacks up to N times" number (2, 4, 6, 8, 10) |
| Arcane Concentration | `mana_cost_pct` (sign −1) | `("all",)` | the % chance (expected free casts): −2 … −10 |
| Master of Elements | `resource` | `("fire", "frost")` | refund % (10, 20, 30) |
| Improved Scorch | `proc_chance` | `("Scorch",)` | the % chance (33, 67, 100) |
| Fingers of Frost | `proc_chance` | `("@chill",)` | 15 per rank text; frozen casts = rank |
Winter's Chill's value combines two numbers; a small parse helper or a special-case rule is fine. Heating Up, Arcane Power and Combustion stay in `UNMODELED` with the reason "handled in mage_rotation" (Combustion: "not modeled yet"). `modifiers_for` gains nothing new: `@sustained` works like `@frozen` (only when `"sustained"` is in `conditions`).

## 3. `src/wowforever/classes/mage_rotation.py`
`rotation(char, filler, *, target_level, assumptions, sustained) -> Rotation`
`@dataclass Rotation`: `dps`, `mana_per_second`, `weaves: dict[str, float]` (casts per minute), `weave_cast_times: dict[str, float]`.

Definitions (stats from `char.stats`, `hit = 1 - miss_chance(level, target_level, hit_pct + mods.hit_bonus)/100`, `crit = (crit_pct + mods.crit_chance_bonus)/100`, `ev(spell, mods)` = `expected_damage(scaled(spell, level), ...)` like `scenarios._cast`):
- `conditions = {"sustained"}` when `sustained`, else empty. Base mods for any spell = `modifiers_for(spell, cls, ranks, conditions)` plus the sustained buffs below.
- **Sustained buffs** (only when `sustained`): Improved Scorch taken and the filler is fire → `damage_pct += 15` on fire spells (5 stacks × 3%). Arcane Power taken → `damage_pct += 30*15/180` and `mana_cost_pct += 30*15/180` on all spells.
- **Filler**: `filler_dps = ev(filler, mods) / cast`, `cast = effective_cast_time(filler, mods)` (channels use their duration, like scenarios).
- **Weaves** (casts per minute `n`, gain per cast `ev(w, mods_w) - filler_dps * cast_w`):
  - Fire Blast: filler is fire and Fire Blast learned → `n = 60 / (cooldown + Wake of Fire's (negative) cooldown value)`; `cast_w` = GCD 1.5.
  - Scorch: `sustained`, Improved Scorch taken, filler is fire → `n = 2 * 100 / chance%` (one landed stack refresh per 30 s); `cast_w = Scorch cast`.
  - Pyroblast: `sustained`, Heating Up and Pyroblast taken, filler is Fireball or Frostfire Bolt → `n = (60 / cast) * hit * crit / 3`; `cast_w = Pyroblast cast * 0.25`.
  - Ice Lance (Fingers of Frost): FoF and Ice Lance taken, filler chills (`slow_pct > 0`) → `n = (60 / cast) * 0.15 * FoF rank`; frozen Ice Lance = damage and coefficient × 4 (+300%), plus Shatter's `@frozen` crit via conditions `{"frozen"}`; `cast_w` = 1.5.
  - If `Σ n * cast_w > 60`, scale every `n` down proportionally.
- `dps = filler_dps + Σ n * gain / 60`.
- **Mana**: per cast cost `c(s) = s.mana_cost * (1 + mods.mana_cost_pct/100)` minus Master of Elements refund `s.mana_cost * moe%/100 * hit * crit` for fire/frost spells. `mana_per_second = c(filler)/cast * (1 - Σ n*cast_w/60) + Σ n * c(w) / 60`.

## 4. Scenarios
In `src/wowforever/scenarios.py`, `raid` uses `rotation(..., sustained=True)` for its DPS and mana drain, and `questing` uses `rotation(..., sustained=False)` for DPS and mana per kill. Keep their existing golden tests passing: with no talents, rotation must equal the single-spell numbers.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
