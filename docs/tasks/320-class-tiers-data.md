# Task #320 (data): PvP tiers for warlock, warrior, paladin and rogue

Make `tests/test_consensus.py` pass. This is a data change: edit only `config/consensus.toml`, and do not edit the tests.

## Why
Research #320 (`docs/research/pvp-core-talents.md`) found Forever-era PvP talent evidence for warlock, warrior, paladin and (partly) rogue. Their tiers and sources go into the per-class consensus file (#321). Hunter, priest, druid and shaman stay without tiers.

## The exact change
Apply this diff with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. It has two hunks:
1. seven source lines after the `prior_research` line in `[sources]`
2. a comment plus sixteen tier sections before the `# ---- archetypes` line

Copy the lines exactly. Don't re-verify context you can see in the diff.

```diff
diff --git a/config/consensus.toml b/config/consensus.toml
index e697ac9..f277549 100644
--- a/config/consensus.toml
+++ b/config/consensus.toml
@@ -34,6 +34,13 @@ barrens_pvp_builds = { url = "https://barrens.chat/viewtopic.php?f=3&t=1475", ki
 barrens_specs_60 = { url = "https://barrens.chat/viewtopic.php?t=2657", kind = "forum", era = "classic", note = "Frost for PvE farming and raiding up to AQ/Naxx; respec freely" }
 wt_tbc_frost_pvp = { url = "https://www.warcrafttavern.com/tbc/guides/pvp-frost-mage/", kind = "guide", era = "tbc", note = "Permafrost core vs melee; Ice Barrier and Ice Block central" }
 prior_research = { url = "docs/research/mage-pvp-leveling-report.md", kind = "research", era = "mixed", note = "Earlier report: Elementalist vs deep Frost trade-off, Burning Soul vs pushback, Impact/Scorch openings" }
+bnet_forever_warlock_musts = { url = "https://us.forums.blizzard.com/en/wow/t/warlock-forever-guide-talents-you-must-take-no-matter-what-build-you-do/2351249", kind = "forum", era = "forever", date = "2026-09-16", note = "Player guide: Improved Corruption in every build; Molten Skin for PvP (with Soul Link and Master Demonologist)" }
+bnet_forever_warlock_pvp = { url = "https://eu.forums.blizzard.com/en/wow/t/warlock-pvp-soul-linkdestro-the-shadow-bolt-problem/632796", kind = "forum", era = "forever", date = "2026-10-01", note = "Players: Soul Link is the PvP pick (SL/SL or 0/21/30 SL/Destro); Decimation, Fel Domination, Conflagrate/Shadowburn burst; Incinerate not worth it" }
+wt_forever_warlock = { url = "https://www.warcrafttavern.com/forever/guides/warlock/", kind = "guide", era = "forever", date = "2026-10", note = "Zephan; Curse of Exhaustion has great PvP utility" }
+wt_classic_warlock_pvp = { url = "https://www.warcrafttavern.com/wow-classic/guides/warlock-pvp/", kind = "guide", era = "classic", note = "Soul Link, Conflagrate, Improved Corruption, Demonic Embrace, Shadowburn in most PvP specs" }
+wt_forever_warrior = { url = "https://www.warcrafttavern.com/forever/guides/warrior/", kind = "guide", era = "forever", date = "2026-10", note = "Passion; Mortal Strike, Improved Hamstring and Spearing Strike very powerful against players; Arms favored for PvP" }
+wt_forever_paladin = { url = "https://www.warcrafttavern.com/forever/guides/paladin/", kind = "guide", era = "forever", date = "2026-10", note = "Passion; Repentance primarily useful for PvP; Voice of Truth (1 point in Purifying Power) especially useful for PvP" }
+bnet_classic_rogue_cb_prep = { url = "https://us.forums.blizzard.com/en/wow/t/cold-blood-prep-question/257787", kind = "forum", era = "classic", date = "2019-08", note = "Players: Cold Blood + Preparation for PvP; Prep resets cooldowns" }
 
 # ---- scenario axis weights ------------------------------------------------------------------
 
@@ -138,6 +145,90 @@ core = ["Improved Frostbolt", "Elemental Precision"]
 strong = ["Ice Shards", "Shatter", "Frostbite", "Permafrost"]
 sources = ["method_forever_leveling", "wt_forever_mage"]
 
+# Other classes (#320, docs/research/pvp-core-talents.md): one list for all four PvP scenarios, since no
+# source separates them. Hunter, priest, druid and shaman have no Forever-era PvP talent evidence yet:
+# no tiers, so no bonus, until sources appear.
+
+[tiers.warlock.wpvp_melee]
+core = ["Soul Link", "Curse of Exhaustion"]
+strong = ["Molten Skin", "Improved Corruption", "Conflagrate", "Shadowburn", "Fel Domination", "Decimation"]
+sources = ["bnet_forever_warlock_pvp", "bnet_forever_warlock_musts", "wt_forever_warlock", "wt_classic_warlock_pvp"]
+
+[tiers.warlock.wpvp_caster]
+core = ["Soul Link", "Curse of Exhaustion"]
+strong = ["Molten Skin", "Improved Corruption", "Conflagrate", "Shadowburn", "Fel Domination", "Decimation"]
+sources = ["bnet_forever_warlock_pvp", "bnet_forever_warlock_musts", "wt_forever_warlock", "wt_classic_warlock_pvp"]
+
+[tiers.warlock.stealth_ambush]
+core = ["Soul Link", "Curse of Exhaustion"]
+strong = ["Molten Skin", "Improved Corruption", "Conflagrate", "Shadowburn", "Fel Domination", "Decimation"]
+sources = ["bnet_forever_warlock_pvp", "bnet_forever_warlock_musts", "wt_forever_warlock", "wt_classic_warlock_pvp"]
+
+[tiers.warlock.battleground]
+core = ["Soul Link", "Curse of Exhaustion"]
+strong = ["Molten Skin", "Improved Corruption", "Conflagrate", "Shadowburn", "Fel Domination", "Decimation"]
+sources = ["bnet_forever_warlock_pvp", "bnet_forever_warlock_musts", "wt_forever_warlock", "wt_classic_warlock_pvp"]
+
+[tiers.warrior.wpvp_melee]
+core = ["Mortal Strike", "Improved Hamstring"]
+strong = ["Spearing Strike"]
+sources = ["wt_forever_warrior"]
+
+[tiers.warrior.wpvp_caster]
+core = ["Mortal Strike", "Improved Hamstring"]
+strong = ["Spearing Strike"]
+sources = ["wt_forever_warrior"]
+
+[tiers.warrior.stealth_ambush]
+core = ["Mortal Strike", "Improved Hamstring"]
+strong = ["Spearing Strike"]
+sources = ["wt_forever_warrior"]
+
+[tiers.warrior.battleground]
+core = ["Mortal Strike", "Improved Hamstring"]
+strong = ["Spearing Strike"]
+sources = ["wt_forever_warrior"]
+
+[tiers.paladin.wpvp_melee]
+core = ["Repentance"]
+strong = ["Voice of Truth"]
+sources = ["wt_forever_paladin"]
+
+[tiers.paladin.wpvp_caster]
+core = ["Repentance"]
+strong = ["Voice of Truth"]
+sources = ["wt_forever_paladin"]
+
+[tiers.paladin.stealth_ambush]
+core = ["Repentance"]
+strong = ["Voice of Truth"]
+sources = ["wt_forever_paladin"]
+
+[tiers.paladin.battleground]
+core = ["Repentance"]
+strong = ["Voice of Truth"]
+sources = ["wt_forever_paladin"]
+
+[tiers.rogue.wpvp_melee]
+core = ["Preparation"]
+strong = ["Cold Blood"]
+sources = ["bnet_classic_rogue_cb_prep"]
+
+[tiers.rogue.wpvp_caster]
+core = ["Preparation"]
+strong = ["Cold Blood"]
+sources = ["bnet_classic_rogue_cb_prep"]
+
+[tiers.rogue.stealth_ambush]
+core = ["Preparation"]
+strong = ["Cold Blood"]
+sources = ["bnet_classic_rogue_cb_prep"]
+
+[tiers.rogue.battleground]
+core = ["Preparation"]
+strong = ["Cold Blood"]
+sources = ["bnet_classic_rogue_cb_prep"]
+
 # ---- archetypes for the shortlist (#28) -----------------------------------------------------
 # deep = a tree with at least `deep` points; hybrid = no deep tree and exactly two trees with at
 # least `hybrid` points. Only hybrids the community actually builds count (math alone doesn't
```

## Environment note
The package is already installed in `.venv` (editable). Before you start, `test_researched_classes_have_pvp_tiers_that_name_their_own_talents` fails with an `AssertionError` on `warlock`. That's the expected failure. Install nothing, make no network calls, and ask for no elevation. Run `.venv/Scripts/python -m pytest tests/test_consensus.py`, then `.venv/Scripts/python -m pytest -m "not slow"` once at the end.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
