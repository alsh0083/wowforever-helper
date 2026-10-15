# Task #318, part D: report and focus use the mage's sides

Make the whole suite pass. This is a refactor, so no score and no build description may change. Edit only these files, in this order:
1. `src/wowforever/report.py`
2. `src/wowforever/focus.py`

Do not edit the tests.

## Why
The duel model is for every class, but its side type is `MageSide`, with mage words in its fields (Thorns sits in `nova_dps`), and `pvp/duel.py` imports the mage rotation (#318, the review's candidate 3). #318 runs in four parts on one branch.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/report.py b/src/wowforever/report.py
index d05681f..0a69178 100644
--- a/src/wowforever/report.py
+++ b/src/wowforever/report.py
@@ -24,7 +24,7 @@ from wowforever.focus import pve_score_fn, pvp_score_fn
 from wowforever.optimizer import optimize_order
 from wowforever.shortlist import build_shortlist
 from wowforever.pvp.battleground import best_battleground
-from wowforever.pvp.duel import best_scenario_scores, load_kits, mage_side, outnumbered_scores
+from wowforever.pvp.duel import best_scenario_scores, load_kits, outnumbered_scores
 from wowforever.rules import check_order, points_available
 from wowforever.scenarios import (Character, aoe_curve, best_rank, default_params, questing, raid,
                                   usable_fillers)
@@ -91,12 +91,13 @@ def score_build(order: Sequence[int], cls: ClassData, spells, stats: StatTable,
             scores[name][level] = {"score": round(result.score, 3), "unit": "0-1",
                                    "components": {k: round(v, 3) for k, v in result.components.items()}}
         fillers = usable_fillers(char, default_params("questing", level).fillers, level, assumptions)
-        for name, result in best_scenario_scores(char, fillers, kits).items():
+        sides = engine("mage").sides(char.stats, spells, cls, char.ranks)
+        for name, result in best_scenario_scores(sides, kits).items():
             scores.setdefault(name, {})[level] = {
                 "score": round(result["score"], 3), "unit": "duel 0-1", "spell": result["spell"],
                 "matchups": {k: round(v, 3) for k, v in result["matchups"].items()}}
         # outnumbered (2v1, #278, #287): a separate score, with the filler that does best
-        two = max(((outnumbered_scores(mage_side(char, f), kits)["score"], f.name) for f in fillers),
+        two = max(((outnumbered_scores(side, kits)["score"], spell) for spell, side in sides),
                   default=(0.5, None))
         scores.setdefault("outnumbered", {})[level] = {"score": round(two[0], 3), "unit": "2v1 0-1", "spell": two[1]}
         d = raid(char, default_params("dungeon", level), assumptions)
diff --git a/src/wowforever/focus.py b/src/wowforever/focus.py
index d36501f..c6256c1 100644
--- a/src/wowforever/focus.py
+++ b/src/wowforever/focus.py
@@ -15,6 +15,7 @@ from wowforever import group
 from wowforever.assumptions import Assumptions
 from wowforever.consensus import Consensus
 from wowforever.pvp.battleground import best_battleground
+from wowforever.classes.mage import duel_side
 from wowforever.pvp.duel import Kit, best_scenario_scores
 from wowforever.scenarios import (Character, aoe_curve, default_params, questing, raid,
                                   usable_fillers)
@@ -45,7 +46,8 @@ def pvp_score_fn(cls: ClassData, stats: Stats, assumptions: Assumptions, kits: l
     def score(ranks: Mapping[int, int]) -> float:
         char = Character(level, stats, cls.spells, cls, dict(ranks))
         fillers = usable_fillers(char, default_params("questing", level).fillers, level, assumptions)
-        duels = best_scenario_scores(char, fillers, kits)  # each duel with its best filler (#97)
+        # each duel with its best filler (#97); the mage's sides at the max level, whatever level `stats` is from
+        duels = best_scenario_scores([(f.name, duel_side(char, f)) for f in fillers], kits)
         scenario_values = [duels[s]["score"] for s in PVP_SCENARIOS]
         scenario_values.append(best_battleground(char, fillers, assumptions)["score"])
         mean = sum(scenario_values) / len(scenario_values)
```

## Environment note
The package is already installed in `.venv` (editable). Parts A-C are done on this branch. Before you start, `report.py` fails to import `mage_side` from `wowforever.pvp.duel`. That is the expected failure. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_focus.py tests/test_outnumbered_report.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
