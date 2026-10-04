# WoW Forever facts the plan depends on

Checked 2026-10-04. Recheck at launch (2026-11-04) and whenever a patch touches these systems. No primary Blizzard page was found for any item below; all come from secondary news/guide sites, so each carries a confidence level.

## Arena: not in Forever

- No arena, rated battlegrounds, or rating ladder announced. PvP is a 14-rank seasonal honor track plus battlegrounds: Warsong Gulch, Arathi Basin, Alterac Valley, and the new 15v15 Darkspear Islands. The beta client contains an unannounced "Mak'gora Arena" record. **Confidence: medium-high** (consistent across many sites).
- **Plan impact:** drop the arena scenario (#27). Revisit if Mak'gora Arena turns into a feature.
- Sources: [Icy Veins PvP overview](https://www.icy-veins.com/wow-forever/pvp-overview), [wowforeverbuilds PvP news](https://wowforeverbuilds.com/news/wow-forever-pvp-a-14-rank-honor-track-every-patch-and-a-new-darkspear-islands-ba), [wow-tracker PvP guide](https://wow-tracker.com/guides/wow-forever-pvp-guide)

## Respec cost: unpublished for launch

- Respecs happen at class trainers. Beta charges 1 silver when talents haven't changed recently; testers report about 5 gold at level 20 in some cases. The launch price is unpublished. Guides assume the Classic curve (1g, 5g, then +5g per respec up to 50g, decaying over time), but that is an assumption. **Confidence: low.**
- **Plan impact:** respec paths (#29) use the Classic curve as a labelled, editable default in `config/`.
- Sources: [wowforeverbuilds respec news](https://wowforeverbuilds.com/news/wow-forever-respecs-already-cost-5-gold-at-level-20-and-beta-testers-say-it-stop), [allthings.how respec guide](https://allthings.how/wow-forever-how-to-respec-your-talents-at-a-class-trainer/), [Blizzard forum thread (players only, no blue posts)](https://us.forums.blizzard.com/en/wow/t/talent-respec/2349746)

## Dual Specialization: from level 40

- Several sites report that Blizzard confirmed Dual Specialization unlocking at level 40, in the 2026-09-30 class deep dives. Still unknown: the unlock price (one site says 50g), swap cost or cooldown, and where you can swap. **Confidence: medium** (several secondary sources agree; no primary text found).
- **Plan impact:** large. From 40, a mage can hold two builds, e.g. AoE grinding plus world PvP, so "level as X, respec to Y" becomes partly "carry X and Y". Tracked as a new decision issue.
- Sources: [wowforeversim dual spec](https://wowforeversim.com/wow-forever-dual-spec), [lfcarry dual spec guide](https://lfcarry.com/guides/wow-forever-dual-spec), [wowsod.pro dual spec](https://wowsod.pro/articles/wow-forever-dual-spec), [MassivelyOP Forever Q&A](https://massivelyop.com/2026/09/19/world-of-warcraft-follows-up-blizzcon-with-wow-retail-and-forever-qa/)

## Mage AoE: weakened; target-cap behavior disputed

- AoE was curbed in Forever. Documented so far, from the client spellbook comparison: Cone of Cold's slow went from 50% for 8s to 40% for 6s, Blizzard's slow was weakened, and max-rank Blizzard damage went from 1192 to 1168. The bigger, disputed claim is a cap: players report AoE damage or threat capping past 4 targets ("no more than 4 mobs should be active at once" as the stated design intent); others say there is no cap and nothing falls off. No Blizzard reply. **Confidence: low** on the cap, **medium-high** on the control nerfs.
- **Plan impact:** no "vanilla AoE build" assumption. The AoE scenario becomes a pack-size curve (#19): value for packs of 2, 3, 4, 5+ mobs, finding the pack size where each build's AoE beats chain single-target. Target caps and per-target damage scaling come from the game data (spell max-targets and effect fields from wago.tools, #10), compared against Classic, not from Classic assumptions. In general, every spell and talent value comes from Forever data; Classic numbers are only used for the comparison.
- Sources: [Blizzard forum, players only, 2026-09-19](https://us.forums.blizzard.com/en/wow/t/blizzard-has-gone-too-far-with-aoe-nerfing-of-arcane-mage/2354784), [Icy Veins Frost guide](https://www.icy-veins.com/wow-forever/frost-mage-ranged-dps-pve-guide), [ForeverChanges mage](https://foreverchanges.pro/class/mage), [ForeverChanges spellbook](https://foreverchanges.pro/spellbook/mage) (cited in `notes/mechanics.md`)
