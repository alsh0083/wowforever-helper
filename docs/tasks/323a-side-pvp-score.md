# Task #323, part A: one PvP score function

Make `tests/test_one_pvp_score.py` pass. Edit only these files, in this order:
1. `src/wowforever/focus.py`

Do not edit the tests.

## Why
Decision #315 (option 1): every class gets the mage's PvP formula, the mean of the four world-PvP duels and the battleground plus the consensus bonus for the class's own core talents (#320). Every class's report gets the duel, battleground, survival and control rows the mage has. Non-mage PvP scores change by design; the mage's must not.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/focus.py b/src/wowforever/focus.py
index c6256c1..8fe6c08 100644
--- a/src/wowforever/focus.py
+++ b/src/wowforever/focus.py
@@ -9,12 +9,12 @@
 
 from __future__ import annotations
 
-from collections.abc import Callable, Mapping
+from collections.abc import Callable, Mapping, Sequence
 
 from wowforever import group
 from wowforever.assumptions import Assumptions
 from wowforever.consensus import Consensus
-from wowforever.pvp.battleground import best_battleground
+from wowforever.pvp.battleground import best_side_battleground
 from wowforever.classes.mage import duel_side
 from wowforever.pvp.duel import Kit, best_scenario_scores
 from wowforever.scenarios import (Character, aoe_curve, default_params, questing, raid,
@@ -36,27 +36,49 @@ def pvp_core_talents(consensus: Consensus, class_name: str = "mage") -> set[str]
             for name in tiers.get(scenario, {}).get("core", ())}
 
 
+def core_talent_ids(cls: ClassData, consensus: Consensus, class_name: str = "mage") -> set[int]:
+    """Talent ids of the class's PvP-core talents (#320); empty for a class without tiers."""
+    return {cls.talent_named(n).talent_id for n in pvp_core_talents(consensus, class_name)
+            if any(t.name == n for t in cls.talents)}
+
+
+def side_pvp_score(sides, kits: Sequence[Kit], level: int, core: set[int], ranks: Mapping[int, int],
+                   consensus: Consensus) -> float:
+    """The PvP score of any class (#315, option 1; #323): the mean of the four world-PvP duels and the
+    battleground, each with the build's best side, plus CONSENSUS_BONUS x the share of the class's core
+    talents taken (0 for a class without tiers)."""
+    duels = best_scenario_scores(sides, kits)
+    values = [duels[s]["score"] for s in PVP_SCENARIOS]
+    values.append(best_side_battleground(sides, level, consensus)["score"])
+    taken = sum(1 for tid in core if ranks.get(tid, 0) > 0)
+    return sum(values) / len(values) + CONSENSUS_BONUS * taken / max(1, len(core))
+
+
 def pvp_score_fn(cls: ClassData, stats: Stats, assumptions: Assumptions, kits: list[Kit],
                  consensus: Consensus) -> ScoreFn:
-    """Score = mean duel score over the PvP scenarios + share of core talents x CONSENSUS_BONUS."""
-    core = {cls.talent_named(n).talent_id for n in pvp_core_talents(consensus)
-            if any(t.name == n for t in cls.talents)}
+    """The mage's PvP score: `side_pvp_score` with one side per usable filler, built at the max level
+    whatever level `stats` is from."""
+    core = core_talent_ids(cls, consensus)
     level = cls.rules.max_level
 
     def score(ranks: Mapping[int, int]) -> float:
         char = Character(level, stats, cls.spells, cls, dict(ranks))
         fillers = usable_fillers(char, default_params("questing", level).fillers, level, assumptions)
-        # each duel with its best filler (#97); the mage's sides at the max level, whatever level `stats` is from
-        duels = best_scenario_scores([(f.name, duel_side(char, f)) for f in fillers], kits)
-        scenario_values = [duels[s]["score"] for s in PVP_SCENARIOS]
-        scenario_values.append(best_battleground(char, fillers, assumptions)["score"])
-        mean = sum(scenario_values) / len(scenario_values)
-        taken = sum(1 for tid in core if ranks.get(tid, 0) > 0)
-        return mean + CONSENSUS_BONUS * taken / max(1, len(core))
+        sides = [(f.name, duel_side(char, f)) for f in fillers]
+        return side_pvp_score(sides, kits, level, core, ranks, consensus)
 
     return score
 
 
+def class_pvp_score(class_name: str, stats, cls: ClassData, ranks: Mapping[int, int], kits: Sequence[Kit],
+                    consensus: Consensus) -> float:
+    """Any other class's PvP score (#323): `side_pvp_score` with its engine's duel side at `stats`' level."""
+    from wowforever.classes import engine
+
+    sides = engine(class_name).sides(stats, cls.spells, cls, ranks)
+    return side_pvp_score(sides, kits, stats.level, core_talent_ids(cls, consensus, class_name), ranks, consensus)
+
+
 def pve_score_fn(cls: ClassData, stats: Stats, assumptions: Assumptions) -> ScoreFn:
     """Score = mean of questing/100, raid/150 and 15/AoE-seconds-for-3-mobs."""
     level = cls.rules.max_level
```

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_one_pvp_score.py` fails to find `side_pvp_score`, and `tests/test_class_pvp.py` fails to import `class_pvp_score`. After this part the `test_one_pvp_score.py` and `test_class_pvp.py` tests pass; part B wires the score into the reports. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_one_pvp_score.py tests/test_class_pvp.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`tests/test_one_pvp_score.py` and `tests/test_class_pvp.py` pass.
