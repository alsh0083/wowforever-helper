# Task #313, part A: group and report ask the class engine

Change how `group.py` and `report.py` read a build's playstyle; the suite keeps passing except the one test part B fixes. This is a refactor, so no score and no build description may change. Edit only these files, in this order:
1. `src/wowforever/group.py`
2. `src/wowforever/report.py`

Do not edit the tests.

## Why
The last hybrid checks and `rotation_output` callers move to `engine(name)`: `.output(...)` and `.playstyle(...)` (#313, in two runs on one branch).

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/group.py b/src/wowforever/group.py
index a9b8da9..a5fde2d 100644
--- a/src/wowforever/group.py
+++ b/src/wowforever/group.py
@@ -276,10 +276,9 @@ def dungeon_dps(class_name: str, stats, cls, ranks: Mapping[int, int], eff: Mapp
     """A build's dungeon DPS with a party's effective buff set: buffed stats, the boss's armor after the
     party's armor debuffs (from its unsundered armor), Curse of the Elements on spell damage, totem procs."""
     from wowforever import melee_scenarios as ms
-    from wowforever.classes import class_module
+    from wowforever.classes import engine
     from wowforever.physical import Target
 
-    module = class_module(class_name)
     if class_name == "mage":
         from wowforever.assumptions import Assumptions
         from wowforever.scenarios import Character, default_params, raid
@@ -291,11 +290,11 @@ def dungeon_dps(class_name: str, stats, cls, ranks: Mapping[int, int], eff: Mapp
     d = ms._config()["dungeon"]
     unsundered = ms._anchor_at(ms._config()["questing"]["anchors"], _level(stats))[0]
     armor = max(0.0, unsundered - armor_reduction(eff))
-    melee_build = isinstance(stats, ms.HybridStats) and ms.main_tree(cls, ranks) in getattr(module, "MELEE_TREES", ())
+    style = engine(class_name).playstyle(cls, ranks)
+    melee_build = isinstance(stats, ms.HybridStats) and style == "melee"
     buffed = buffed_stats(class_name, stats, eff, melee_build=melee_build)
-    out = ms.rotation_output(class_name, buffed, cls.spells, cls, ranks, Target(d["target_level_offset"], armor)).dps
-    caster = getattr(module, "ENGINE", None) == "spell" and not melee_build
-    if caster:
+    out = engine(class_name).output(buffed, cls.spells, cls, ranks, Target(d["target_level_offset"], armor)).dps
+    if style == "caster":
         return out * magic_multiplier(eff)
     physical = buffed.melee if isinstance(buffed, ms.HybridStats) else buffed
     if class_name in MELEE_CLASSES and _is_physical(physical) and not (class_name == "shaman" and melee_build):
@@ -372,12 +371,6 @@ def compositions(weights: Mapping[str, Mapping[str, int]]) -> list[tuple[float,
     return out
 
 
-def player_kind(class_name: str, melee_build: bool, stats) -> str:
-    if class_name == "hunter":
-        return "ranged"
-    return "melee" if melee_build or _is_physical(stats) else "caster"
-
-
 def _pick(member_options: Sequence[Sequence[dict]], kind: str) -> list[dict]:
     prefs = PREFERENCES[kind]
     picks = []
@@ -449,13 +442,12 @@ def _drop_for(class_name: str, cls, ranks: Mapping[int, int]) -> frozenset[str]:
 
 
 def _kind_for(class_name: str, stats, cls, ranks) -> str:
-    from wowforever import melee_scenarios as ms
-    from wowforever.classes import class_module
+    """How the build fights, which picks its party's buff preferences: melee, ranged or caster."""
+    from wowforever.classes import engine
 
-    melee_trees = getattr(class_module(class_name), "MELEE_TREES", ())
-    melee_build = isinstance(stats, ms.HybridStats) and ms.main_tree(cls, ranks) in melee_trees
-    inner = stats.melee if melee_build else (stats.caster if isinstance(stats, ms.HybridStats) else stats)
-    return player_kind(class_name, melee_build, inner)
+    if class_name == "mage":               # until the mage has its class engine (#316)
+        return "caster"
+    return engine(class_name).playstyle(cls, ranks)
 
 
 def _dist_for(class_name: str, stats, cls, ranks):
diff --git a/src/wowforever/report.py b/src/wowforever/report.py
index 3ebf991..d05681f 100644
--- a/src/wowforever/report.py
+++ b/src/wowforever/report.py
@@ -18,6 +18,7 @@ from wowforever.builds import Build
 from wowforever.calc.pvp_axes import control, survival
 from wowforever.checklist import checklist
 from wowforever.classes import class_module as _class_module
+from wowforever.classes import engine
 from wowforever.consensus import Consensus
 from wowforever.focus import pve_score_fn, pvp_score_fn
 from wowforever.optimizer import optimize_order
@@ -524,7 +525,6 @@ def add_stat_weights(class_name: str, cls: ClassData, builds: Sequence[Build], r
                  "PvP": lambda s, r: pvp_score(class_name, s, cls.spells, cls, r, load_kits(level=s.level))}
     else:
         table, score = None, {}
-    melee_trees = getattr(module, "MELEE_TREES", ())
     generic = sw.generic_weights(class_name)
     leveling_score = (lambda s, r, run=questing_at(class_name, cls): run(s, r)["score"]) if table is not None else None
     for b in report["builds"]:
@@ -534,7 +534,8 @@ def add_stat_weights(class_name: str, cls: ClassData, builds: Sequence[Build], r
             continue
         b["stat_weights"] = sw.build_weights(
             class_name, cls, b, table, leveling_score if b.get("mode") == "leveling" else score[focus], CHECKPOINTS,
-            melee_build=lambda ranks: bool(melee_trees) and ms.main_tree(cls, ranks) in melee_trees)
+            melee_build=lambda ranks: table is not None and class_name != "mage"
+            and engine(class_name).playstyle(cls, ranks) == "melee")
     for b in report["builds"]:
         b["stat_priority"] = _stat_priority(b, variant.get(b["id"]))
 
```

## Environment note
The package is already installed in `.venv` (editable). Before you start, `test_scenarios_ask_the_engine_with_no_class_chain` fails because `melee_scenarios.rotation_output` still exists. It still fails after this part; part B fixes it. That is expected. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_group.py tests/test_class_engine.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
The only failure in `-m "not slow"` is `test_scenarios_ask_the_engine_with_no_class_chain`.
