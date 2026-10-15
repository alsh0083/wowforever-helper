# PvP-core talents per class: what the evidence supports (research, 2026-10-14)

For #320. The question: can each class get a consensus PvP-core list backed as well as mage's, so that the consensus bonus (#315, option 1) doesn't favor mage just because mage was researched first?

Sources follow the owner's rules (#23): reputable guides and forums, robots.txt-permitted, no Wowhead, no Reddit, no gold or boost sellers. The search also turned up mmoexp, misti.services, mmonster, lfcarry, wowvendor and rankedboost; all are sellers, so all are excluded. Talent status ("same", "changed", "moved", "new") is the dataset's `classic_status` for build 1.60.1.70291. Classic evidence counts at full confidence only for "same" talents (consensus.py's rule).

## What mage's list rests on

Mage's PvP tiers (`config/consensus.toml`, `[tiers.mage.*]`) cite:
- one Forever forum thread (`bnet_forever_mage_pvp`: players say Ice Barrier is needed against rogue openers);
- two Classic/TBC sources (`barrens_pvp_builds`, `wt_tbc_frost_pvp`);
- an earlier internal report.

Warcraft Tavern's Forever mage guide adds one PvP talent claim: Fingers of Frost with Ice Lance. Of the core talents, only Improved Frost Nova is unchanged from Classic. Ice Barrier, Cold Snap and Permafrost changed, and Ice Block moved.

So the bar is modest: **one Forever-era source naming the talents for PvP, plus Classic consensus.**

## Evidence by class

| Class | Forever-era PvP talent claims (allowed sources) | Classic evidence usable at full confidence | Meets mage's bar? |
|---|---|---|---|
| Warlock | Two Forever forum threads (Sept 16 and Oct 1, 2026): Soul Link is the PvP pick, with Molten Skin, Decimation, Fel Domination/Master Summoner and the Conflagrate/Shadowburn package. WT Forever guide: Curse of Exhaustion "great PvP utility". | WT Classic warlock PvP guide: Soul Link, Conflagrate, Improved Corruption, Demonic Embrace, Shadowburn (all changed in Forever) | **Yes**, the best-backed after mage |
| Warrior | WT Forever guide: Mortal Strike, Improved Hamstring and Spearing Strike are "very powerful against other players"; Arms "favored for PvP" | Mortal Strike and Improved Hamstring are unchanged | **Yes** |
| Paladin | WT Forever guide: Repentance "primarily useful for PvP"; Voice of Truth "especially useful if you enjoy PvPing" | none needed | **Yes**, narrowly (one guide) |
| Rogue | None. The Forever forum thread (Sept 22) argues design, with no PvP picks. WT Forever names racials only. | Classic forum (2019): Cold Blood + Preparation for PvP. Preparation is unchanged; Cold Blood changed. | **Partly**: Preparation only |
| Hunter | None. WT Forever names racials only. | No Classic hunter PvP talent source found among allowed sites (WT's are WotLK) | **No** |
| Priest | None. WT Forever names no PvP talents. | WT Classic world-PvP guide names Martyrdom (changed), Unbreakable Will (gone), Blackout (moved), all as minor | **No** |
| Druid | None | None found | **No** |
| Shaman | None | None found | **No** |

## Proposed tiers (for #321's per-class format)

Applied to all four PvP scenarios (`wpvp_melee`, `wpvp_caster`, `stealth_ambush`, `battleground`). No source separates them the way mage's do.

- **Warlock:** core Soul Link, Curse of Exhaustion. Strong: Molten Skin, Improved Corruption, Conflagrate, Shadowburn, Fel Domination, Decimation. Sources: the two Forever forum threads, WT Forever, WT Classic.
- **Warrior:** core Mortal Strike, Improved Hamstring. Strong: Spearing Strike. Source: WT Forever.
- **Paladin:** core Repentance. Strong: Voice of Truth. Source: WT Forever.
- **Rogue:** core Preparation (Classic forum; unchanged talent). Strong: Cold Blood (changed, so low confidence).
- **Hunter, priest, druid, shaman:** empty for now, with a note. Their bonus is 0 until a Forever-era source names PvP talents.

## Is the bonus fair?

**Not across classes, as things stand.** With these tiers:
- mage, warlock, warrior and paladin builds can earn up to +0.10;
- rogue can earn up to +0.10, but only from one talent;
- hunter, priest, druid and shaman earn 0.

How much that matters depends on where the bonus is used:

- **Today the bonus only ranks builds within a class.** It feeds the PvP focus score that picks each class's model build and stat weights (`report.py`, `focus.pvp_score_fn`). No dashboard view compares PvP numbers between classes, so a class with no tiers gets purely model-driven PvP picks. That's no worse than today, and not unfair to anyone.
- **#323 will put PvP rows for every class side by side.** If those rows include the bonus, mage, warlock, warrior and paladin would gain up to 0.10 from research coverage alone.

## Recommendation

1. **Keep the bonus for picking builds within a class.** That's what it's for, and an empty tier simply means no community nudge.
2. **Leave it out of every number shown for comparing classes.** #323's per-class PvP rows show the duel and battleground mean without the bonus. The bonus appears only as its own line ("community PvP talents: 3/4 taken").
3. **Fill tiers only from evidence that meets mage's bar,** and record each class's coverage in the report so the dashboard can say "no community PvP data yet".
4. **Re-run this check after launch.** Forever-era guides for the missing classes should appear once level-60 PvP exists. #320 stays the place to add them.

## Sources

Forever era:
- WoW Forever forums: [Warlock talents you must take](https://us.forums.blizzard.com/en/wow/t/warlock-forever-guide-talents-you-must-take-no-matter-what-build-you-do/2351249) (2026-09-16), [Warlock PvP: Soul Link/Destro](https://eu.forums.blizzard.com/en/wow/t/warlock-pvp-soul-linkdestro-the-shadow-bolt-problem/632796) (2026-10-01), [Rogues in WoW Forever](https://us.forums.blizzard.com/en/wow/t/rogues-in-wow-forever/2357811) (2026-09-22)
- Warcraft Tavern Forever guides: [warrior](https://www.warcrafttavern.com/forever/guides/warrior/), [paladin](https://www.warcrafttavern.com/forever/guides/paladin/), [warlock](https://www.warcrafttavern.com/forever/guides/warlock/), [mage](https://www.warcrafttavern.com/forever/guides/mage/), [rogue](https://www.warcrafttavern.com/forever/guides/rogue/), [hunter](https://www.warcrafttavern.com/forever/guides/hunter/), [priest](https://www.warcrafttavern.com/forever/guides/priest/), [druid](https://www.warcrafttavern.com/forever/guides/druid/), [shaman](https://www.warcrafttavern.com/forever/guides/shaman/) (no PvP talent claims in the last five)

Classic:
- [WT Classic warlock PvP guide](https://www.warcrafttavern.com/wow-classic/guides/warlock-pvp/)
- [WT Classic world PvP guide](https://www.warcrafttavern.com/wow-classic/guides/world-pvp/)
- [Classic forum: Cold Blood + Prep](https://us.forums.blizzard.com/en/wow/t/cold-blood-prep-question/257787) (2019)
