# Task #131 (part 3): rogue rotation

Make `tests/test_rogue_rotation.py` pass without breaking the rest of the suite. Edit `src/wowforever/physical.py` and create `src/wowforever/classes/rogue_rotation.py`. `config/rogue.toml` is written already. Do not edit the tests or config.

## Why
The rogue's sustained single-target DPS comes from white swings plus an energy cycle: builders until 5 combo points, then a finisher, with Slice and Dice kept up. Every number comes from the parsed spells (#131 part 1), the talent effect rules (part 2), the stat table (#129), the physical combat table (#130) and `config/rogue.toml`.

## 1. `physical.py` additions (keyword arguments, defaults keep today's behaviour)
- `white_swing(..., dodge_reduction=0.0)` and `yellow_attack(..., dodge_reduction=0.0, crit_damage_pct=0.0)`. `ranged_shot` passes `crit_damage_pct` through.
- `dodge = max(0, dodge[i] - dodge_reduction)`.
- In `yellow_attack` the crit multiplier becomes `1 + (crit_multiplier - 1) * (1 + crit_damage_pct / 100)`, so Lethality's +30% turns 2.0 into 2.3.

## 2. `classes/rogue_rotation.py`
```python
@dataclass(frozen=True)
class RogueRotation:
    dps: float
    white_dps: float
    yellow_dps: float
    builder: str              # spell name
    energy_per_second: float
    cycles_per_second: float  # builder-to-finisher cycles

def rogue_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                   ranks: Mapping[int, int], target: Target) -> RogueRotation
```
Throughout, `value(talent, kind, applies)` is the per-rank value of a taken talent's effect of that kind whose `applies_to` contains `applies`, or 0 when untaken. Sum across talents where it says "sum". Spells are the best rank learned by `stats.level` (`scenarios.best_rank`).

1. **Attacker:**
   - `Attacker(stats.level, stats.attack_power, stats.crit_pct + sum crit_chance "all", stats.hit_pct + sum hit_chance "all")`.
   - `dodge_reduction` = sum of `dodge_reduction` "all".
   - The target's armor is cut by `armor_pen` "all": `replace(target, armor=target.armor * (1 - pen / 100))`.
2. **Haste:**
   - `h = (1 + snd.haste_pct / 100)` if Slice and Dice is learned, else 1.
   - Times `(1 + bf.haste_pct/100 * bf.duration / bf.cooldown)` if Blade Flurry is taken.
3. **White DPS:**
   - Main hand: `white_swing(stats.main_hand, A, T, dual_wield=DW, dodge_reduction=dr) * h / mh_speed`.
   - Plus, when there's an off hand: `white_swing(stats.off_hand, A, T, dual_wield=True, off_hand=True, damage_pct=value(DW Spec, damage_pct, "@off_hand"), dodge_reduction=dr) * h / oh_speed`.
   - `DW` means both hands are present.
4. **Energy:** `E = energy_per_second * (1 + ar.bonus_pct/100 * ar.duration / ar.cooldown if Adrenaline Rush taken else 1)`.
5. **Builder:** Mutilate if taken and learned; otherwise Hemorrhage if taken; otherwise Sinister Strike.
   - **Per hit:** `norm = (min + max)/2 + attack_power / 14 * speed_n`, with `speed_n` = `normalized_speed.dagger` for Mutilate and `.one_hand` otherwise.
     - Main-hand stats for the first hit; Mutilate's second hit uses the off hand.
     - `base = (norm + spell.weapon_bonus) * (spell.weapon_pct / 100 if spell.weapon_pct else 1)`.
   - **Damage:** `builder_ev = Σ over hits yellow_attack(base, A, T, crit_bonus=Σ crit_chance for the spell name, damage_pct=Σ damage_pct for the spell name, crit_damage_pct=Σ crit_damage_pct for the spell name, dodge_reduction=dr)`.
   - **Cost:** `cost = spell.energy_cost + Σ energy_cost for the spell name`.
   - **Combo points per use:**
     - `land` = probability one hit lands, from the same miss/dodge rules as `yellow_attack`.
     - `c` = that hit's crit chance as a fraction.
     - Mutilate's crit chance is `1 - (1 - c)**2` over its two hits.
     - `cp = spell.combo_points * land + land * c_use * value(Seal Fate, proc_chance, "@builder_crit") / 100`.
6. **Finisher:** Eviscerate at `k = finisher_combo_points`.
   - `base = (min + max)/2 + spell.per_combo_point * k`.
   - `evis_ev = yellow_attack(base, A, T, damage_pct=Σ damage_pct for "Eviscerate", dodge_reduction=dr)`.
   - Cost `evis.energy_cost`.
   - Relentless Strikes refunds `value(RS, resource, "@finisher")/100 * k * 25` energy per finisher.
7. **Cycle:**
   - Ruthlessness: `start = value(Ruthlessness, proc_chance, "@finisher")/100`.
   - `n = (k - start) / cp` builders per cycle.
   - `cycle_energy = n * cost + evis.energy_cost - refund`.
   - `cycles_per_second = E / cycle_energy`.
   - **Slice and Dice** (if learned):
     - `snd_seconds = (snd.duration + snd_seconds_per_combo_point * k) * (1 + value(Improved SnD, duration, "Slice and Dice") / 100)`.
     - The share of cycles that end in Eviscerate is `f = max(0, 1 - (1 / snd_seconds) / cycles_per_second)`.
   - Without Slice and Dice, `f = 1`.
8. **Yellow DPS:** `cycles_per_second * (n * builder_ev + f * evis_ev)`.
9. **Total:** `dps = white_dps + yellow_dps`.

Not modeled yet, with comments in the code: poisons, Backstab (needs the main-hand weapon type), Hack and Slash, and Blade Flurry's second target.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_rogue_rotation.py` fails on an import of `wowforever.classes.rogue_rotation`. That's the expected failure. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Start with `physical.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_rogue_rotation.py tests/test_physical.py`, then run the full suite once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
