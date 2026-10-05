# Task #132 (part 1): hunter damage talents as effect rules

Make `tests/test_hunter_effects.py` pass without breaking the rest of the suite. Edit `src/wowforever/classes/hunter.py` and `src/wowforever/schema.py`. Do not edit the tests or fixtures.

## Why
The hunter rotation (part 2) needs the numbers from the hunter's damage talents. They come from the Forever rank text through `EffectRule` regexes, the same way #131 part 2 did for the rogue. See `classes/rogue.py`.

## 1. `schema.py`
Add two effect kinds to `EFFECT_KINDS`, each with a comment:
- `"ap_from_int_pct"`: attack power gained as % of Intellect (Careful Aim).
- `"stat_pct"`: % more of a primary stat. `applies_to` names the stat (Lightning Reflexes: agility).

## 2. `classes/hunter.py`
Move these talents from `UNMODELED` into `TALENT_EFFECTS` (applies-to tuples exactly as listed; `sign=-1` where noted):

| Talent | kind | applies_to | number in the text |
|---|---|---|---|
| Lethal Attacks | crit_chance | ("all",) | "critical strike chance with all attacks by N%" |
| Careful Aim | ap_from_int_pct | ("all",) | "Attack Power by N% of your Intellect" |
| Mortal Shots | crit_damage_pct | ("@ranged",) | "critical strike damage bonus on all ranged abilities by N%" |
| Ranged Weapon Specialization | damage_pct | ("@ranged",) | "damage you deal with ranged weapons by N%" |
| Barrage | damage_pct | ("Multi-Shot", "Aimed Shot", "Volley") | "Multi-Shot, Aimed Shot, and Volley abilities by N%" |
| Improved Arcane Shot | cooldown | ("Arcane Shot",) | "cooldown of your Arcane Shot by N sec (sign=-1)" |
| Efficiency | mana_cost_pct | ("@shot", "@sting", "@melee") | "Mana cost of your Shots, Stings, and melee abilities by N% (sign=-1)" |
| Lone Wolf | damage_pct | ("@no_pet",) | "N% increased damage with all attacks" |
| Savage Strikes | crit_chance | ("@melee",) | "critical strike chance of all your melee abilities by N%" |
| Lacerating Strikes | dot_pct | ("Mongoose Bite",) | "Bleed for damage equal to N% of the damage" |
| Improved Stings | damage_pct | ("Serpent Sting",) | "damage of your Serpent Sting ability by N%" |
| Lightning Reflexes | stat_pct | ("agility",) | "Agility by N%" |
| Surefooted | hit_chance | ("all",) | "hit chance by N%" |
| Improved Tracking | damage_pct | ("@tracked",) | "tracked creature type is increased by N%" |
| Focused Fire | damage_pct | ("@with_pet",) | "damage you and your pet deal by N%" |
| Unleashed Fury | damage_pct | ("@pet",) | "damage done by your pets and hawks by N%" |
| Ferocity | crit_chance | ("@pet",) | "critical strike chance of your pets and hawks by N%" |

Predator's Edge gets two rules: `crit_damage_pct` ("@melee",) from "melee critical strike damage by N%", and `damage_pct` ("@off_hand",) from "Off Hand weapon damage by N%".

Keep every other talent in `UNMODELED`. Coverage must stay complete: `attach_effects` reports nothing. Check your regexes against every rank's text, not only the last.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_hunter_effects.py` fails because the rules don't exist yet. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Start with `schema.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_hunter_effects.py tests/test_hunter.py`, then run the full suite once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
