# Task #399 (part 2): Hammer of Wrath and Champion of the Light for Retribution

Make `tests/test_hammer_of_wrath.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order; run the test file at the end, then the fast suite once. Paladin
  regression pins (`tests/test_kit_stats.py`, opponent kits, `tests/test_class_engine.py` totals) may move; Claude
  re-derives them.
- Before you start, the tests in `tests/test_hammer_of_wrath.py` fail.

## Why
Hammer of Wrath is only usable at or below 20% health (its spell description), so the model counts it on cooldown
for 20% of the fight, the same execute-phase share the talents use (#392). It's a Holy spell: spell hit table,
spell crit at x1.5 with the melee row's crit (best effort, like Enhancement's Earth Shock). Champion of the Light
gives spell power from 30% of Intellect (`spell_power_from`, the kind Mental Quickness uses); Hammer of Wrath and
Consecration's ticks use it through their coefficients. Mana stays out (Retribution doesn't track mana yet).

## Step 1: `config/paladin.toml`
Append:
```toml
# Hammer of Wrath is usable at or below this % of the target's health (spell description); counted for that share
# of the fight (#399)
hammer_of_wrath_health_pct = 20.0
```

## Step 2: `src/wowforever/classes/paladin.py`
Add to `TALENT_EFFECTS`:
```python
    "Champion of the Light": (
        EffectRule("spell_power_from", r"by up to (\d+(?:\.\d+)?)% of your Intellect", ("intellect",)),
    ),
```
and delete the `UNMODELED` line for `"Champion of the Light"`.

## Step 3: `src/wowforever/classes/paladin_rotation.py`
1. Add `from wowforever.calc.ev import miss_chance` above `from wowforever.melee_stats import MeleeStats` (or with the
   other `wowforever` imports, in alphabetical order).
2. Directly after the line `    holy, used = 0.0, []` add:
```python
    spell_power = stats.intellect * total("spell_power_from", "intellect") / 100   # Champion of the Light (#399)
```
3. Directly before the line `    aoe: tuple[str, ...] = ()` add:
```python
    hammer = best_rank(spells, "Hammer of Wrath", stats.level)
    if hammer is not None and hammer.cooldown > 0:
        # usable in the execute phase only: on cooldown for that share of the fight (#399)
        hit = 1 - miss_chance(stats.level, stats.level + target.level_diff, stats.hit_pct) / 100
        spell_crit = min(1.0, (stats.crit_pct + total("crit_chance", "all")) / 100)
        damage = (((hammer.min_damage + hammer.max_damage) / 2 + hammer.coefficient * spell_power)
                  * (1 + (all_pct + total("damage_pct", "Hammer of Wrath")) / 100))
        holy += (c["hammer_of_wrath_health_pct"] / 100 * hit * damage * (1 + spell_crit * 0.5)
                 / max(hammer.cooldown, 1.5))
        used.append("Hammer of Wrath")
```
4. In the Consecration block, the line
   `        holy += (consecration.periodic_damage * (1 + (all_pct + total("damage_pct", "Consecration")) / 100)`
   becomes
   `        holy += ((consecration.periodic_damage + consecration.periodic_coefficient * spell_power)`
   followed by a new line
   `                 * (1 + (all_pct + total("damage_pct", "Consecration")) / 100)`
   (the next line, `                 * pack / period)`, stays).
5. In the module docstring, `Not modeled yet: Consecration against one mob, Exorcism and Hammer of Wrath (target or
   health` / `limits), Vindication's attack power, Twist of Light's echo, Champion of the Light's spell power, and`
   become `Hammer of Wrath counts for the execute-phase share of the fight (#399), with Champion of the Light's spell
   power. Not modeled yet: Consecration against one mob, Exorcism (undead and demons only), Vindication's attack
   power, Twist of Light's echo, and` — keep the following line about mana as it is, and keep lines under 110
   characters.

Nothing else changes.

## Done when
- `tests/test_hammer_of_wrath.py` passes; no other new failures apart from paladin pins.
