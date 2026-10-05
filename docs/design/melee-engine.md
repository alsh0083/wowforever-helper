# Melee, ranged and pet engine (#111)

Stage 2 of the alts (docs/planning/2026-10-05.md, Q7). The mage calculator models spell damage. Rogue and hunter builds need physical damage before they get scored routes and model picks. This page fixes the scope and the order of work. Each step is its own issue with hand-worked golden tests first, as v0/v1 were.

## What the community builds need (from #104, #108)
| Build | Damage model |
|---|---|
| Rogue Combat Swords (PvE/PvP) | dual-wield white swings, Sinister Strike, Slice and Dice, Eviscerate, Blade Flurry, Adrenaline Rush, Hack and Slash extra attacks |
| Rogue Mutilate Seal Fate | dual-wield daggers, Mutilate, poisons (Deadly/Instant), Seal Fate combo points |
| Rogue Subtlety Preparation (PvP) | openers (Ambush, Cheap Shot, Premeditation), Hemorrhage/Backstab, burst windows |
| Hunter Survival Lone Wolf | **petless dual-wield melee**: Raptor Strike, Mongoose Bite + Lacerating Strikes bleed, Strider Kick, Lone Wolf +20% |
| Hunter Marksmanship | Auto Shot, Aimed/Arcane/Multi-Shot, Serpent Sting; Trueshot Aura; Lone Wolf |
| Hunter Beast Mastery | pet damage (Bestial Wrath, Frenzy, Ferocity, Unleashed Fury) plus hunter shots |

## Steps
1. **Weapon and stat data (#129).**
   - Fetch the ItemDamage* tables, then compute weapon damage ranges and speeds from ItemSparse (ItemLevel, ItemDelay, DmgVariance, quality).
   - Build per-class stat tables (agility, strength, attack power, ranged AP, melee and ranged crit and hit, main-hand, off-hand and ranged weapons) from real Forever gear, the way #68 did for the mage.
2. **Physical combat table (#130):** expected damage of a white swing, a yellow ability and a ranged shot.
   - Against a level+N target: miss (with the dual-wield penalty), dodge, parry (melee from the front only), glancing (white only, level+3), crit and hit.
   - Armor mitigation from target armor.
   - Constants are Classic values in `config/assumptions.toml` style, each with a source.
3. **Rogue rotation (#131):**
   - Energy regen (20 per 2 s), builders and finishers, combo points per builder (crit with Seal Fate, Ruthlessness), Relentless Strikes refunds.
   - Slice and Dice uptime.
   - Effect rules for the rogue talents now in UNMODELED.
4. **Hunter rotation (#132):**
   - Auto Shot plus shot weaving and mana.
   - Survival's petless dual-wield melee.
   - A simple pet for Beast Mastery: pet DPS from pet level and talents.
5. **Scenarios and report (#133):**
   - Questing, where food downtime replaces drinking for rogues; hunters drink.
   - Dungeon and raid DPS.
   - Rogue and hunter get `ENGINE = True`, so they gain the archetype × focus shortlist and model picks.
6. **Rogue/hunter PvP (#134):**
   - The duel model from the attacker's side, with each class's own kit built from its build, against the opponent kits including a mage kit.

## Not in scope
Gear optimization, set bonuses (#70), and anything already deferred for the mage, such as Monte Carlo (#32).
