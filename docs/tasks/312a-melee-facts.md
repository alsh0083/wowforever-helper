# Task #312, part A: facts for rogue, hunter, warrior and paladin

Make `test_facts_describe_the_rotation_each_build_runs` pass for rogue, hunter, warrior and paladin. This is a refactor, so no score and no build description may change. Edit only these files, in this order:
1. `src/wowforever/classes/rogue.py`
2. `src/wowforever/classes/hunter.py`
3. `src/wowforever/classes/warrior.py`
4. `src/wowforever/classes/paladin.py`

Do not edit the tests.

## Why
`describe.rotation_facts` re-runs every class's rotation in its own `if class_name ==` chain. Each class engine now answers `facts` itself (#312, in three runs on one branch).

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/classes/rogue.py b/src/wowforever/classes/rogue.py
index 91db215..3cf5227 100644
--- a/src/wowforever/classes/rogue.py
+++ b/src/wowforever/classes/rogue.py
@@ -155,7 +155,6 @@ SKILL_LINES = (253, 38, 39, 40)
 
 
 # --- class engine (#309): this module is the rogue's ClassEngine ------------------------------------
-from wowforever.classes.engines import facts_later as facts  # noqa: E402
 
 
 def playstyle(cls, ranks) -> str:
@@ -174,3 +173,12 @@ def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
     from wowforever.classes.engines import pack_aoe
 
     return pack_aoe(output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)
+
+
+def facts(stats, cls, ranks):
+    from wowforever.classes.rogue_rotation import rogue_rotation
+    from wowforever.physical import Target
+
+    r = rogue_rotation(stats, cls.spells, cls, ranks, Target(0, 0))
+    return {"kind": "rogue", "builder": r.builder,
+            "split": {"auto-attacks": r.white_dps / r.dps, "abilities and poisons": r.yellow_dps / r.dps}}
diff --git a/src/wowforever/classes/hunter.py b/src/wowforever/classes/hunter.py
index c66eb6e..14033a3 100644
--- a/src/wowforever/classes/hunter.py
+++ b/src/wowforever/classes/hunter.py
@@ -129,7 +129,6 @@ SKILL_LINES = (50, 163, 51)
 
 
 # --- class engine (#310): this module is the hunter's ClassEngine ------------------------------------
-from wowforever.classes.engines import facts_later as facts  # noqa: E402
 
 
 def has_pet(cls, ranks) -> bool:
@@ -155,3 +154,13 @@ def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
     from wowforever.classes.engines import pack_aoe
 
     return pack_aoe(output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)
+
+
+def facts(stats, cls, ranks):
+    from wowforever.classes.hunter_rotation import hunter_rotation
+    from wowforever.physical import Target
+
+    pet = has_pet(cls, ranks)
+    r = hunter_rotation(stats, cls.spells, cls, ranks, Target(0, 0), pet=pet)
+    split = {"pet": r.pet_dps / r.dps} if pet and r.dps else {}
+    return {"kind": "hunter", "mode": r.mode, "pet": pet, "split": split}
diff --git a/src/wowforever/classes/warrior.py b/src/wowforever/classes/warrior.py
index 37e0419..90efdaf 100644
--- a/src/wowforever/classes/warrior.py
+++ b/src/wowforever/classes/warrior.py
@@ -122,7 +122,6 @@ ICON_OVERRIDES: dict[str, str] = {}
 
 
 # --- class engine (#309): this module is the warrior's ClassEngine ------------------------------------
-from wowforever.classes.engines import facts_later as facts  # noqa: E402
 
 
 def playstyle(cls, ranks) -> str:
@@ -141,3 +140,12 @@ def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
     from wowforever.classes.engines import pack_aoe
 
     return pack_aoe(output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)
+
+
+def facts(stats, cls, ranks):
+    from wowforever.classes.warrior_rotation import warrior_rotation
+    from wowforever.physical import Target
+
+    r = warrior_rotation(stats, cls.spells, cls, ranks, Target(0, 0))
+    return {"kind": "abilities", "abilities": list(r.abilities),
+            "split": {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps}}
diff --git a/src/wowforever/classes/paladin.py b/src/wowforever/classes/paladin.py
index a4c1662..1be9f75 100644
--- a/src/wowforever/classes/paladin.py
+++ b/src/wowforever/classes/paladin.py
@@ -110,7 +110,6 @@ CAVEAT = ("Retribution model (#175): a two-hander's white swings with Seal of Co
 
 
 # --- class engine (#309): this module is the paladin's ClassEngine ------------------------------------
-from wowforever.classes.engines import facts_later as facts  # noqa: E402
 
 
 def playstyle(cls, ranks) -> str:
@@ -129,3 +128,12 @@ def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
     from wowforever.classes.engines import pack_aoe
 
     return pack_aoe(output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)
+
+
+def facts(stats, cls, ranks):
+    from wowforever.classes.paladin_rotation import paladin_rotation
+    from wowforever.physical import Target
+
+    r = paladin_rotation(stats, cls.spells, cls, ranks, Target(0, 0))
+    return {"kind": "abilities", "abilities": list(r.abilities),
+            "split": {"auto-attacks": r.white_dps / r.dps, "Holy damage": r.holy_dps / r.dps}}
```

## Environment note
The package is already installed in `.venv` (editable). Before you start, `test_facts_describe_the_rotation_each_build_runs` fails for all eight classes with `NotImplementedError` from the `facts` placeholder. After this part it still fails for druid, priest, shaman and warlock, and `test_describe_asks_the_engine_for_every_class_but_mage` still fails; parts B and C fix those. That is expected. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_class_engine.py -k facts`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
In `tests/test_class_engine.py`, the facts test passes for rogue, hunter, warrior and paladin. The only failures left in `-m "not slow"` are the four caster/hybrid facts cases and the describe test.
