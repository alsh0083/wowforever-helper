# Task #312, part C: describe asks the class engine

Make the whole suite pass. This is a refactor, so no score and no build description may change. Edit only these files, in this order:
1. `src/wowforever/describe.py`

Do not edit the tests.

## Why
`describe.rotation_facts` re-runs every class's rotation in its own `if class_name ==` chain. Each class engine now answers `facts` itself (#312, in three runs on one branch).

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/describe.py b/src/wowforever/describe.py
index 1f36892..d40d122 100644
--- a/src/wowforever/describe.py
+++ b/src/wowforever/describe.py
@@ -188,9 +188,7 @@ def class_best(builds: Sequence[Mapping[str, Any]]) -> dict[str, float]:
 def rotation_facts(class_name: str, cls: ClassData, ranks: Mapping[int, int], stats: Any,
                    scores: Mapping[str, Any]) -> dict[str, Any]:
     """What the class engine's rotation does at level 60 against a level-60 target."""
-    from . import melee_scenarios as ms
-    from .classes import class_module
-    from .physical import Target
+    from .classes import engine
 
     if class_name == "mage":
         def cell(s: str) -> str | None:
@@ -199,56 +197,7 @@ def rotation_facts(class_name: str, cls: ClassData, ranks: Mapping[int, int], st
 
         return {"kind": "mage", "questing": cell("questing"), "raid": cell("raid"), "aoe": cell("aoe"),
                 "pvp": cell("wpvp_caster")}
-    module = class_module(class_name)
-    target = Target(0, 0)
-    if isinstance(stats, ms.HybridStats):
-        if ms.main_tree(cls, ranks) in module.MELEE_TREES:
-            if class_name == "druid":
-                from .classes.druid_rotation import cat_rotation
-
-                r = cat_rotation(stats.melee, cls.spells, cls, ranks, target)
-                return {"kind": "cat", "builder": r.builder,
-                        "split": {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps}}
-            from .classes.shaman_rotation import enhancement_rotation
-
-            r = enhancement_rotation(stats.melee, cls.spells, cls, ranks, target)
-            return {"kind": "enhancement", "split": {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps,
-                                                     "spells and procs": r.spell_dps / r.dps}}
-        stats = stats.caster
-    if getattr(module, "ENGINE", None) == "spell":
-        from .caster import caster_rotation
-
-        r = caster_rotation(class_name, stats, cls.spells, cls, ranks, target)
-        plan = module.ROTATION
-        return {"kind": "caster", "dots": [s for s in r.spells if s in plan.get("dots", ())],
-                "cooldowns": [s for s in r.spells if s in plan.get("cooldowns", ())],
-                "filler": next((s for s in r.spells if s in plan.get("fillers", ())), None)}
-    if class_name == "rogue":
-        from .classes.rogue_rotation import rogue_rotation
-
-        r = rogue_rotation(stats, cls.spells, cls, ranks, target)
-        return {"kind": "rogue", "builder": r.builder,
-                "split": {"auto-attacks": r.white_dps / r.dps, "abilities and poisons": r.yellow_dps / r.dps}}
-    if class_name == "hunter":
-        from .classes.hunter import has_pet
-        from .classes.hunter_rotation import hunter_rotation
-
-        pet = has_pet(cls, ranks)
-        r = hunter_rotation(stats, cls.spells, cls, ranks, target, pet=pet)
-        split = {"pet": r.pet_dps / r.dps} if pet and r.dps else {}
-        return {"kind": "hunter", "mode": r.mode, "pet": pet, "split": split}
-    if class_name in ("warrior", "paladin"):
-        from .classes.paladin_rotation import paladin_rotation
-        from .classes.warrior_rotation import warrior_rotation
-
-        if class_name == "warrior":
-            r = warrior_rotation(stats, cls.spells, cls, ranks, target)
-            split = {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps}
-        else:
-            r = paladin_rotation(stats, cls.spells, cls, ranks, target)
-            split = {"auto-attacks": r.white_dps / r.dps, "Holy damage": r.holy_dps / r.dps}
-        return {"kind": "abilities", "abilities": list(r.abilities), "split": split}
-    return {}
+    return engine(class_name).facts(stats, cls, ranks)
 
 
 def _buff_names() -> dict[str, str]:
```

## Environment note
The package is already installed in `.venv` (editable). Parts A and B are already done on this branch. Before you start, `test_describe_asks_the_engine_for_every_class_but_mage` fails. That is the expected failure. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_class_engine.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
