# Task #131 (part 2): rogue damage talents as effect rules

Make `tests/test_rogue_effects.py` pass without breaking the rest of the suite. Edit `src/wowforever/classes/rogue.py` and `src/wowforever/schema.py`. Do not edit the tests or fixtures.

## Why
The rogue rotation (part 3) needs the numbers from the rogue's damage talents. Like the mage, the numbers come from the Forever rank text through `EffectRule` regexes, one value per rank, never hard-coded. See `classes/mage.py` for the style.

## 1. `schema.py`
Add three effect kinds to `EFFECT_KINDS`, each with a comment:
- `"energy_cost"`: flat change to an ability's energy cost (negative = cheaper).
- `"dodge_reduction"`: percentage points off the target's dodge and parry.
- `"armor_pen"`: % of the target's armor ignored.

## 2. `classes/rogue.py`
Move these talents from `UNMODELED` into `TALENT_EFFECTS`. Pattern-match the number in each rank's text. Applies-to tuples are exactly as listed.

| Talent | kind | applies_to | number in the text |
|---|---|---|---|
| Malice | crit_chance | ("all",) | "critical strike chance with all attacks and Poisons by N%" |
| Lethality | crit_damage_pct | ("Sinister Strike", "Gouge", "Backstab", "Mutilate", "Ghostly Strike", "Hemorrhage") | "critical strike damage bonus of ... by N%" |
| Aggression | damage_pct | ("Sinister Strike", "Backstab", "Eviscerate") | "damage of your ... by N%" |
| Improved Eviscerate | damage_pct | ("Eviscerate",) | "Eviscerate ability by N%" |
| Dual Wield Specialization | damage_pct | ("@off_hand",) | "off-hand weapon by N%" |
| Precision | hit_chance | ("all",) | "chance to hit by N%" |
| Weapon Expertise | dodge_reduction | ("all",) | "Dodged or Parried by N%" |
| Opportunity | damage_pct | ("Backstab", "Garrote", "Ambush", "Mutilate") | "abilities by N%" |
| Relentless Strikes | resource | ("@finisher",) | "N% chance per Combo Point" |
| Ruthlessness | proc_chance | ("@finisher",) | "N% chance to add a Combo Point" |
| Seal Fate | proc_chance | ("@builder_crit",) | "N% chance to add an additional Combo Point" |
| Puncturing Wounds | crit_chance ("Backstab",), crit_chance ("Mutilate",), proc_chance ("@backstab_combo",) | see column 2 | "Backstab by N%", "Mutilate by N%", "Backstab a N% chance" |
| Improved Sinister Strike | energy_cost, `sign=-1` | ("Sinister Strike",) | "Energy cost ... by N" |
| Improved Slice and Dice | duration | ("Slice and Dice",) | "duration ... by N%" |
| Vile Poisons | damage_pct | ("@poison",) | "damage dealt by your poisons by N%" |
| Murder | damage_pct | ("@humanoid",) | "damage dealt by N%" |
| Serrated Blades | armor_pen | ("all",) | "ignore N% of your target's Armor" |
| Improved Ambush | crit_chance | ("Ambush",) | "Ambush ability by N%" |

Puncturing Wounds gets three rules: crit_chance for Backstab, crit_chance for Mutilate, and proc_chance for the extra combo point.

Keep every other talent in `UNMODELED` as it is. Coverage must stay complete: `attach_effects` reports nothing. Check your regexes against every rank's text: print them with the command in `docs/tasks/103-rogue.md`, using `t.rank_text` for all ranks.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_rogue_effects.py` fails because the rules don't exist yet. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Start with `schema.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_rogue_effects.py tests/test_rogue.py`, then run the full suite once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
