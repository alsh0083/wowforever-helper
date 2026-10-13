# Task #287 (report part): the outnumbered (2v1) score in every report

Make `tests/test_outnumbered_report.py` (marked slow; run it by name) pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/report.py` and `dashboard/template.html`. The test docstring has the rule.

## Why
#278 added the outnumbered score (`duel.outnumbered_scores`, `class_pvp.outnumbered_score`), but no report shows it. Each scored build now gets an "outnumbered" row at every checkpoint, next to the duel scenarios, and the dashboard labels it "Outnumbered (2v1)". `melee_report` now uses the module-level `load_kits` import (its later local import would make the name unbound in the new loop code).

## Change
Make exactly the changes in this diff (`-` lines go, `+` lines come, the rest is context). Turn it into `tools/apply_patch.py` hunks: same files, same order, context copied from the files.

```diff
diff --git a/dashboard/template.html b/dashboard/template.html
index 5bc10ff..31e66ce 100644
--- a/dashboard/template.html
+++ b/dashboard/template.html
@@ -64,7 +64,7 @@ try{talented=Math.max(0,Math.min(5,parseInt(localStorage.getItem('wow-forever-ta
 RULES.first_talent_level=BASE_FIRST_LEVEL-talented;
 const BUILDS=DATA.builds;
 const TREE_CLASS=THEME.trees;
-const SCENARIO_LABEL={questing:'Questing',aoe:'AoE',raid:'Raid',dungeon:'Dungeon (5-player group)',battleground:'Battleground',survival:'Survival',control:'Control',wpvp_melee:'Duel vs melee',wpvp_melee_they_open:'Duel vs melee, they open',wpvp_caster:'Duel vs caster',stealth_ambush:'Stealth ambush'};
+const SCENARIO_LABEL={questing:'Questing',aoe:'AoE',raid:'Raid',dungeon:'Dungeon (5-player group)',battleground:'Battleground',survival:'Survival',control:'Control',wpvp_melee:'Duel vs melee',wpvp_melee_they_open:'Duel vs melee, they open',wpvp_caster:'Duel vs caster',stealth_ambush:'Stealth ambush',outnumbered:'Outnumbered (2v1)'};
 const SELECTED_KEY=CLASS==='mage'?'wow-forever-selected-build':'wow-forever-selected-build-'+CLASS;
 const saveKey=id=>'wow-forever-save-v5-'+id;
 
diff --git a/src/wowforever/report.py b/src/wowforever/report.py
index cebd0f3..e5ba370 100644
--- a/src/wowforever/report.py
+++ b/src/wowforever/report.py
@@ -23,7 +23,7 @@ from wowforever.focus import pve_score_fn, pvp_score_fn
 from wowforever.optimizer import optimize_order
 from wowforever.shortlist import build_shortlist
 from wowforever.pvp.battleground import best_battleground
-from wowforever.pvp.duel import best_scenario_scores, load_kits
+from wowforever.pvp.duel import best_scenario_scores, load_kits, mage_side, outnumbered_scores
 from wowforever.rules import check_order, points_available
 from wowforever.scenarios import (Character, aoe_curve, best_rank, default_params, questing, raid,
                                   usable_fillers)
@@ -94,6 +94,10 @@ def score_build(order: Sequence[int], cls: ClassData, spells, stats: StatTable,
             scores.setdefault(name, {})[level] = {
                 "score": round(result["score"], 3), "unit": "duel 0-1", "spell": result["spell"],
                 "matchups": {k: round(v, 3) for k, v in result["matchups"].items()}}
+        # outnumbered (2v1, #278, #287): a separate score, with the filler that does best
+        two = max(((outnumbered_scores(mage_side(char, f), kits)["score"], f.name) for f in fillers),
+                  default=(0.5, None))
+        scores.setdefault("outnumbered", {})[level] = {"score": round(two[0], 3), "unit": "2v1 0-1", "spell": two[1]}
         d = raid(char, default_params("dungeon", level), assumptions)
         g = group.grouped_dungeon("mage", stats.at(level), cls, ranks_at(order, level, cls))
         scores.setdefault("dungeon", {})[level] = {**g, "unit": "dps", "spell": d.details["spell"],
@@ -321,6 +325,7 @@ def melee_report(class_name: str, cls: ClassData, builds: Sequence[Build], datas
     from wowforever import melee_scenarios as ms
     from wowforever.consensus import Consensus
     from wowforever.optimizer import optimize_order
+    from wowforever.pvp.class_pvp import outnumbered_score
     from wowforever.rules import points_available
     from wowforever.shortlist import build_shortlist
 
@@ -358,6 +363,8 @@ def melee_report(class_name: str, cls: ClassData, builds: Sequence[Build], datas
             scores["dungeon"][level] = {**group.grouped_dungeon(class_name, stats, cls, ranks), "unit": "dps",
                                         "solo": round(ms.dungeon(class_name, stats, spells, cls, ranks), 1)}
             seconds, spell = ms.aoe(class_name, stats, spells, cls, ranks)
+            two = outnumbered_score(class_name, stats, spells, cls, ranks, load_kits(level=level))
+            scores.setdefault("outnumbered", {})[level] = {"score": round(two, 3), "unit": "2v1 0-1"}
             scores["aoe"][level] = {"score": round(seconds, 1), "unit": "seconds (3-mob pack)", "spell": spell,
                                     "lower_better": True}
             if level == top:
@@ -368,7 +375,6 @@ def melee_report(class_name: str, cls: ClassData, builds: Sequence[Build], datas
     arch = Consensus.load().archetypes
     stats_top = table.at(top)
     from wowforever.pvp.class_pvp import pvp_score
-    from wowforever.pvp.duel import load_kits
 
     kits = load_kits()
     fns = {"PvE": lambda ranks: ms.pve_score(class_name, stats_top, spells, cls, ranks),
```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_outnumbered_report.py` fails with `KeyError: 'outnumbered'`. That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), one file at a time, with each file's hunks in file order. `dashboard/template.html` has very long lines: for its hunk, use only the changed line, no context.

## Done when
`.venv/Scripts/python -m pytest tests/test_outnumbered_report.py` (about 10 s) passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`. Do not run the other slow tests.
