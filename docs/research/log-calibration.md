# Model vs Forever Logs (#172)

Checked 2026-10-07 with `wowforever validate-logs` and `validate-logs --boss-only` against the
Forever Logs public statistics (phase 1, role dps; 1,265 parses, 1,253 boss-only; refreshed the same
day after new uploads, with the improved talent orders). Beta cap is
level 30, so only the level-20 and level-30 checkpoints have logs. Rows with fewer than 25 parses
are left out below.

## The fair comparison is the stronger parses on bosses

The model plays an optimized build without mistakes, so it should sit near the strong parses
(p75–p90), not the average. And it scores one target, so boss fights are the like-for-like data: whole
dungeons include trash pulls where AoE multiplies DPS.

| Spec | Level | Parses | Model / p90 (all fights) | Model / p90 (bosses only) |
|---|---|---|---|---|
| Hunter Marksmanship | 20 | 74 | 0.97 | 1.02 |
| Hunter Marksmanship | 30 | 35 | 0.81 | 0.89 |
| Hunter Beast Mastery | 20 | 57 | 1.15 | 1.29 |
| Hunter Beast Mastery | 30 | 39 | 1.16 | 1.28 |
| Mage Frost | 20 | 28 | 0.58 | 1.02 |
| Mage Arcane | 20 | 30 | 0.72 | 1.24 |
| Mage Fire | 20 | 25 | 0.87 | 1.07 |
| Warlock Affliction | 20 | 43 | 1.08 | 1.18 |
| Druid Feral Combat | 20 | 69 | 0.92 | 0.93 |
| Rogue Combat | 20 | 60 | 0.67 | 0.71 |
| Rogue Combat | 30 | 40 | 0.59 | 0.79 |
| Rogue Assassination | 20 | 85 | 0.67 | 0.67 |
| Rogue Assassination | 30 | 45 | 0.60 | 0.60 |
| Shaman Enhancement | 20 | 107 | 0.59 | 0.68 |
| Shaman Enhancement | 30 | 78 | 0.65 | 0.69 |
| Paladin Retribution | 20 | 91 | 0.68 | 0.75 |
| Paladin Retribution | 30 | 65 | 0.74 | 0.79 |
| Warrior Arms | 20 | 51 | 0.29 | 0.48 |
| Warrior Arms | 30 | 26 | 0.30 | 0.71 |

## Findings

- **Casters and ranged track the logs** once trash is left out (0.9–1.3 of p90). The mage's gap on
  whole dungeons was AoE on trash, which the single-target dungeon score doesn't count.
- **Melee is still low on bosses** (0.6–0.8 of p90; Retribution rose from 0.5 once the talent order
  took Seal of Command at 20). The model's level-20 rogue checks out by
  hand (16-DPS main hand, 205 AP, ~16% crit, ~360 boss armor after Sunder: ~33 white DPS plus
  specials and poisons, about the model's 52), so the gap isn't an arithmetic bug.
- **Party help is the likely cause.** The per-ability damage in the owner-saved reports
  (`data/logs/foreverlogs.json`) shows damage melee get from their group:
  - Flametongue Attack (a shaman's Flametongue Totem) is 4–12% of a rogue's and paladins' damage.
  - Windfury Weapon is 20% of a level-30 Enhancement shaman's damage.
  - Blazewind Blast (5–8% on paladins) looks Forever-specific; source unknown.
  - Attack-power buffs (Battle Shout, Blessing of Might, Strength of Earth) don't show as
    abilities but raise every hit.

  The dungeon scenario models a tank's Sunder Armor but no party buffs. Buffs and totems lift melee
  far more than casters, which matches the split.
- **Arms warrior is the outlier**: 0.48 of p90 on level-20 bosses and 0.29 on whole dungeons
  (51 parses), so beyond party buffs its single-target and multi-target Rage model needs a look.
- Logs bucket players by the dungeon's typical level; players above that level (common in
  leveling dungeons) raise the logged numbers for every class alike.

## Next steps

1. Add party buffs to the melee dungeon scenario (one attack-power buff at its rank for the level,
   and Flametongue Totem), then compare again. Decide how many buffs a typical pug has.
2. Identify Blazewind Blast (item, talent or Forever change).
3. Per-ability checks against `events:read` once the owner's request is granted.

Refresh: the statistics are fetched on demand with the owner's key (about 40 requests per mode,
free tier). Raw responses stay in `data/cache/foreverlogs/` and are not redistributed.

## With party buffs (#218-#221, 2026-10-07)

The dungeon score now models a weighted 5-player group with Forever's own buff values (see
docs/planning/2026-10-07-party-buffs.md). Same logs (1,265 parses; 1,253 boss-only), rows with 25+ parses:

| Spec | Level | Parses | Model / p90 (all fights) | Model / p90 (bosses only) | Bosses only, before |
|---|---|---|---|---|---|
| Hunter Marksmanship | 20 | 74 | 0.99 | 1.04 | 1.02 |
| Hunter Marksmanship | 30 | 35 | 0.85 | 0.94 | 0.89 |
| Hunter Beast Mastery | 20 | 57 | 1.17 | 1.32 | 1.29 |
| Hunter Beast Mastery | 30 | 39 | 1.23 | 1.36 | 1.28 |
| Mage Frost | 20 | 28 | 0.66 | 1.16 | 1.02 |
| Mage Arcane | 20 | 30 | 0.82 | 1.42 | 1.24 |
| Mage Fire | 20 | 25 | 0.97 | 1.19 | 1.07 |
| Warlock Affliction | 20 | 43 | 1.13 | 1.23 | 1.18 |
| Druid Feral Combat | 20 | 69 | 0.97 | 0.99 | 0.93 |
| Rogue Combat | 20 | 60 | 0.70 | 0.74 | 0.71 |
| Rogue Combat | 30 | 40 | 0.66 | 0.88 | 0.76 |
| Rogue Assassination | 20 | 85 | 0.71 | 0.71 | 0.67 |
| Rogue Assassination | 30 | 45 | 0.67 | 0.67 | 0.60 |
| Shaman Enhancement | 20 | 107 | 0.62 | 0.71 | 0.68 |
| Shaman Enhancement | 30 | 78 | 0.71 | 0.76 | 0.69 |
| Paladin Retribution | 20 | 91 | 0.73 | 0.80 | 0.75 |
| Paladin Retribution | 30 | 65 | 0.83 | 0.89 | 0.79 |
| Warrior Arms | 20 | 51 | 0.31 | 0.51 | 0.48 |
| Warrior Arms | 30 | 26 | 0.34 | 0.81 | 0.71 |

- **Melee moved up most at level 30**, where Windfury Totem, Grace of Air and stronger shouts arrive.
  At 20 few group buffs exist yet, so the gain is small.
- **Casters went from about 1.0 to 1.2-1.4 at level 20.** That's mostly Arcane Intellect, Kings and
  Curse of the Elements, which a level-20 pug often lacks in practice.
- **Still open:** melee is 0.7-0.9 of the strong boss parses, and Arms warrior at 20 is 0.51. Arms'
  Rage model is the next suspect. Logs bucket players by the dungeon's typical level, so over-levelled
  players also raise the logged numbers.

