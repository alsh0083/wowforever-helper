# Task #323, part B: every class's report gets the PvP rows and the one PvP score

Make the whole suite pass. Non-mage PvP scores change by design; the mage's must not. Edit only these files, in this order:
1. `src/wowforever/report.py`
2. `src/wowforever/pvp/class_pvp.py`

Do not edit the tests.

## Why
Decision #315 (option 1): every class gets the mage's PvP formula, the mean of the four world-PvP duels and the battleground plus the consensus bonus for the class's own core talents (#320). Every class's report gets the duel, battleground, survival and control rows the mage has. Non-mage PvP scores change by design; the mage's must not.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/report.py b/src/wowforever/report.py
index 0a69178..fc73ac6 100644
--- a/src/wowforever/report.py
+++ b/src/wowforever/report.py
@@ -15,15 +15,15 @@ from typing import Any
 from wowforever import group
 from wowforever.assumptions import Assumptions
 from wowforever.builds import Build
-from wowforever.calc.pvp_axes import control, survival
+from wowforever.calc.pvp_axes import control, side_control, side_survival, survival
 from wowforever.checklist import checklist
 from wowforever.classes import class_module as _class_module
 from wowforever.classes import engine
 from wowforever.consensus import Consensus
-from wowforever.focus import pve_score_fn, pvp_score_fn
+from wowforever.focus import class_pvp_score, pve_score_fn, pvp_score_fn
 from wowforever.optimizer import optimize_order
 from wowforever.shortlist import build_shortlist
-from wowforever.pvp.battleground import best_battleground
+from wowforever.pvp.battleground import best_battleground, best_side_battleground
 from wowforever.pvp.duel import best_scenario_scores, load_kits, outnumbered_scores
 from wowforever.rules import check_order, points_available
 from wowforever.scenarios import (Character, aoe_curve, best_rank, default_params, questing, raid,
@@ -365,7 +365,22 @@ def melee_report(class_name: str, cls: ClassData, builds: Sequence[Build], datas
             scores["dungeon"][level] = {**group.grouped_dungeon(class_name, stats, cls, ranks), "unit": "dps",
                                         "solo": round(ms.dungeon(class_name, stats, spells, cls, ranks), 1)}
             seconds, spell = ms.aoe(class_name, stats, spells, cls, ranks)
-            two = outnumbered_score(class_name, stats, spells, cls, ranks, load_kits(level=level))
+            kits = load_kits(level=level)
+            two = outnumbered_score(class_name, stats, spells, cls, ranks, kits)
+            sides = engine(class_name).sides(stats, spells, cls, ranks)
+            for name, result in best_scenario_scores(sides, kits).items():
+                scores.setdefault(name, {})[level] = {
+                    "score": round(result["score"], 3), "unit": "duel 0-1",
+                    "matchups": {k: round(v, 3) for k, v in result["matchups"].items()}}
+            side = sides[0][1]
+            for name, axis in (("survival", side_survival), ("control", side_control)):
+                result = axis(side)
+                scores.setdefault(name, {})[level] = {"score": round(result.score, 3), "unit": "0-1",
+                                                      "components": {k: round(v, 3) for k, v in result.components.items()}}
+            bg = best_side_battleground(sides, level)
+            scores.setdefault("battleground", {})[level] = {
+                "score": round(bg["score"], 3), "unit": "0-1",
+                "components": {k: round(v, 3) for k, v in bg["components"].items()}}
             scores.setdefault("outnumbered", {})[level] = {"score": round(two, 3), "unit": "2v1 0-1"}
             scores["aoe"][level] = {"score": round(seconds, 1), "unit": "seconds (3-mob pack)", "spell": spell,
                                     "lower_better": True}
@@ -376,11 +391,11 @@ def melee_report(class_name: str, cls: ClassData, builds: Sequence[Build], datas
 
     arch = Consensus.load().archetypes
     stats_top = table.at(top)
-    from wowforever.pvp.class_pvp import pvp_score
 
     kits = load_kits()
+    consensus = Consensus.load()
     fns = {"PvE": lambda ranks: ms.pve_score(class_name, stats_top, spells, cls, ranks),
-           "PvP": lambda ranks: pvp_score(class_name, stats_top, spells, cls, ranks, kits)}
+           "PvP": lambda ranks: class_pvp_score(class_name, stats_top, cls, ranks, kits, consensus)}
     slots = build_shortlist(cls, list(builds), fns, margin=SHORTLIST_MARGIN, deep=arch["deep"],
                             hybrid=arch["hybrid"], recognized=tuple(hybrids))
     names = {t.talent_id: t.name for t in cls.talents}
@@ -511,7 +526,6 @@ def add_stat_weights(class_name: str, cls: ClassData, builds: Sequence[Build], r
     scores (healers, tanks, routes-only classes) get the class's generic gear weights."""
     from wowforever import melee_scenarios as ms
     from wowforever import stat_weights as sw
-    from wowforever.pvp.class_pvp import pvp_score
 
     variant = {b.id: b.variant for b in builds}
     module = _class_module(class_name)
@@ -521,9 +535,9 @@ def add_stat_weights(class_name: str, cls: ClassData, builds: Sequence[Build], r
         score = {"PvE": lambda s, r: pve_score_fn(cls, s, assumptions)(r),
                  "PvP": lambda s, r: pvp_score_fn(cls, s, assumptions, load_kits(level=s.level), consensus)(r)}
     elif getattr(module, "ENGINE", False) in ("melee", "spell"):
-        table = ms.stat_table(class_name)
+        table, consensus = ms.stat_table(class_name), Consensus.load()
         score = {"PvE": lambda s, r: ms.pve_score(class_name, s, cls.spells, cls, r),
-                 "PvP": lambda s, r: pvp_score(class_name, s, cls.spells, cls, r, load_kits(level=s.level))}
+                 "PvP": lambda s, r: class_pvp_score(class_name, s, cls, r, load_kits(level=s.level), consensus)}
     else:
         table, score = None, {}
     generic = sw.generic_weights(class_name)
diff --git a/src/wowforever/pvp/class_pvp.py b/src/wowforever/pvp/class_pvp.py
index 8af5e17..e79ee0b 100644
--- a/src/wowforever/pvp/class_pvp.py
+++ b/src/wowforever/pvp/class_pvp.py
@@ -19,12 +19,11 @@ from pathlib import Path
 
 from wowforever.assumptions import Assumptions
 from wowforever.calc.ev import BASE_CRIT_BONUS_PCT, GCD_SECONDS
-from wowforever.focus import PVP_SCENARIOS
 from wowforever.classes import engine
 from wowforever.melee_scenarios import build_stats
 from wowforever.melee_stats import MeleeStats
 from wowforever.physical import Target, armor_factor
-from wowforever.pvp.duel import Control, Kit, Side, lockout_seconds, outnumbered_scores, scenario_scores
+from wowforever.pvp.duel import Control, Kit, Side, lockout_seconds, outnumbered_scores
 from wowforever.scenarios import best_rank
 from wowforever.schema import ClassData, SpellRank
 from wowforever.toml_cache import load_toml
@@ -208,15 +207,7 @@ def class_side(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank],
     )
 
 
-def pvp_score(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
-              ranks: Mapping[int, int], kits: Sequence[Kit]) -> float:
-    """Mean duel score over the four world-PvP scenarios (as the mage's, without battlegrounds)."""
-    side = class_side(class_name, stats, spells, cls, ranks)
-    scores = scenario_scores(side, kits)
-    return sum(scores[s]["score"] for s in PVP_SCENARIOS) / len(PVP_SCENARIOS)
-
-
 def outnumbered_score(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                       ranks: Mapping[int, int], kits: Sequence[Kit]) -> float:
-    """Mean 2v1 score over pairs of kits (#278), a separate score next to pvp_score."""
+    """Mean 2v1 score over pairs of kits (#278), a separate score next to the PvP score (focus.class_pvp_score)."""
     return outnumbered_scores(class_side(class_name, stats, spells, cls, ranks), kits)["score"]
```

## Environment note
The package is already installed in `.venv` (editable). Part A (`focus.side_pvp_score`, `class_pvp_score`) is done on this branch. The fast suite already passes before this part; the slow `tests/test_melee_report.py` expects the new rows. Run only `-m "not slow"` (the slow tests take minutes). Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_one_pvp_score.py tests/test_class_pvp.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
