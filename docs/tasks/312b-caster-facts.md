# Task #312, part B: facts for priest, warlock, druid and shaman

Make `test_facts_describe_the_rotation_each_build_runs` pass for every class. This is a refactor, so no score and no build description may change. Edit only these files, in this order:
1. `src/wowforever/classes/engines.py`
2. `src/wowforever/classes/priest.py`
3. `src/wowforever/classes/warlock.py`
4. `src/wowforever/classes/druid.py`
5. `src/wowforever/classes/shaman.py`

Do not edit the tests.

## Why
`describe.rotation_facts` re-runs every class's rotation in its own `if class_name ==` chain. Each class engine now answers `facts` itself (#312, in three runs on one branch).

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/classes/engines.py b/src/wowforever/classes/engines.py
index c713de6..882ead4 100644
--- a/src/wowforever/classes/engines.py
+++ b/src/wowforever/classes/engines.py
@@ -73,6 +73,25 @@ def hybrid_aoe(class_name: str, melee_trees: Sequence[str], output: Callable[...
     return caster_aoe(class_name, row, spells, cls, ranks, pack=pack, mob_hp=mob_hp)
 
 
-def facts_later(stats: Any, cls: ClassData, ranks: Mapping[int, int]) -> dict[str, Any]:
-    """Placeholder until the adapters gain their facts (#312)."""
-    raise NotImplementedError("rotation facts move behind the class engine in #312")
+def caster_facts(class_name: str, plan: Mapping[str, Sequence[str]], stats: Any, cls: ClassData,
+                 ranks: Mapping[int, int]) -> dict[str, Any]:
+    """The caster rotation's DoTs, cooldowns and filler at level 60 against a level-60 target."""
+    from wowforever.caster import caster_rotation
+
+    r = caster_rotation(class_name, stats, cls.spells, cls, ranks, Target(0, 0))
+    return {"kind": "caster", "dots": [s for s in r.spells if s in plan.get("dots", ())],
+            "cooldowns": [s for s in r.spells if s in plan.get("cooldowns", ())],
+            "filler": next((s for s in r.spells if s in plan.get("fillers", ())), None)}
+
+
+def hybrid_facts(class_name: str, melee_trees: Sequence[str], melee_facts: Callable[..., dict[str, Any]],
+                 plan: Mapping[str, Sequence[str]], stats: Any, cls: ClassData,
+                 ranks: Mapping[int, int]) -> dict[str, Any]:
+    """A melee build's melee facts on its melee row, else the caster facts on the caster row."""
+    from wowforever.melee_scenarios import HybridStats
+
+    if isinstance(stats, HybridStats):
+        if melee_build(melee_trees, cls, ranks):
+            return melee_facts(stats.melee, cls, ranks)
+        stats = stats.caster
+    return caster_facts(class_name, plan, stats, cls, ranks)
diff --git a/src/wowforever/classes/priest.py b/src/wowforever/classes/priest.py
index 1c24db0..2b17e03 100644
--- a/src/wowforever/classes/priest.py
+++ b/src/wowforever/classes/priest.py
@@ -135,7 +135,6 @@ CAVEAT = ("Caster model (#163): Shadow Word: Pain and Devouring Plague kept up,
 
 
 # --- class engine (#311): this module is the priest's ClassEngine ------------------------------------
-from wowforever.classes.engines import facts_later as facts  # noqa: E402
 
 
 def playstyle(cls, ranks) -> str:
@@ -152,3 +151,9 @@ def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
     from wowforever.classes.engines import caster_aoe
 
     return caster_aoe("priest", stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp)
+
+
+def facts(stats, cls, ranks):
+    from wowforever.classes.engines import caster_facts
+
+    return caster_facts("priest", ROTATION, stats, cls, ranks)
diff --git a/src/wowforever/classes/warlock.py b/src/wowforever/classes/warlock.py
index 85e9df2..46696ec 100644
--- a/src/wowforever/classes/warlock.py
+++ b/src/wowforever/classes/warlock.py
@@ -133,7 +133,6 @@ CAVEAT = ("Caster model (#163, #165): Corruption, Bane of Agony and Immolate kep
 
 
 # --- class engine (#311): this module is the warlock's ClassEngine ------------------------------------
-from wowforever.classes.engines import facts_later as facts  # noqa: E402
 
 
 def playstyle(cls, ranks) -> str:
@@ -150,3 +149,9 @@ def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
     from wowforever.classes.engines import caster_aoe
 
     return caster_aoe("warlock", stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp)
+
+
+def facts(stats, cls, ranks):
+    from wowforever.classes.engines import caster_facts
+
+    return caster_facts("warlock", ROTATION, stats, cls, ranks)
diff --git a/src/wowforever/classes/druid.py b/src/wowforever/classes/druid.py
index e239d46..e78df57 100644
--- a/src/wowforever/classes/druid.py
+++ b/src/wowforever/classes/druid.py
@@ -174,7 +174,6 @@ CAVEAT = ("Balance (#166): Moonfire and Insect Swarm kept up, then Starfire or W
 
 
 # --- class engine (#311): this module is the druid's ClassEngine ------------------------------------
-from wowforever.classes.engines import facts_later as facts  # noqa: E402
 
 
 def playstyle(cls, ranks) -> str:
@@ -204,3 +203,18 @@ def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
 
     return hybrid_aoe("druid", MELEE_TREES, output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp,
                       armor=armor)
+
+
+def _melee_facts(stats, cls, ranks):
+    from wowforever.classes.druid_rotation import cat_rotation
+    from wowforever.physical import Target
+
+    r = cat_rotation(stats, cls.spells, cls, ranks, Target(0, 0))
+    return {"kind": "cat", "builder": r.builder,
+            "split": {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps}}
+
+
+def facts(stats, cls, ranks):
+    from wowforever.classes.engines import hybrid_facts
+
+    return hybrid_facts("druid", MELEE_TREES, _melee_facts, ROTATION, stats, cls, ranks)
diff --git a/src/wowforever/classes/shaman.py b/src/wowforever/classes/shaman.py
index db43970..3a38d22 100644
--- a/src/wowforever/classes/shaman.py
+++ b/src/wowforever/classes/shaman.py
@@ -133,7 +133,6 @@ CAVEAT = ("Elemental (#167): Flame Shock kept up, Lava Burst and Chain Lightning
 
 
 # --- class engine (#311): this module is the shaman's ClassEngine ------------------------------------
-from wowforever.classes.engines import facts_later as facts  # noqa: E402
 
 
 def playstyle(cls, ranks) -> str:
@@ -162,3 +161,18 @@ def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
 
     return hybrid_aoe("shaman", MELEE_TREES, output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp,
                       armor=armor)
+
+
+def _melee_facts(stats, cls, ranks):
+    from wowforever.classes.shaman_rotation import enhancement_rotation
+    from wowforever.physical import Target
+
+    r = enhancement_rotation(stats, cls.spells, cls, ranks, Target(0, 0))
+    return {"kind": "enhancement", "split": {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps,
+                                             "spells and procs": r.spell_dps / r.dps}}
+
+
+def facts(stats, cls, ranks):
+    from wowforever.classes.engines import hybrid_facts
+
+    return hybrid_facts("shaman", MELEE_TREES, _melee_facts, ROTATION, stats, cls, ranks)
```

## Environment note
The package is already installed in `.venv` (editable). Part A (rogue, hunter, warrior, paladin) is already done on this branch. Before you start, the facts test fails for druid, priest, shaman and warlock with `NotImplementedError`. After this part only `test_describe_asks_the_engine_for_every_class_but_mage` still fails; part C fixes it. That is expected. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_class_engine.py -k facts`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
The only failure left in `-m "not slow"` is `test_describe_asks_the_engine_for_every_class_but_mage`.
