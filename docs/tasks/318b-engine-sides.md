# Task #318, part B: every class engine lists its duel sides

Add `sides` to the ClassEngine interface and to the eight non-mage class modules. This is a refactor, so no score and no build description may change. Edit only these files, in this order:
1. `src/wowforever/classes/__init__.py`
2. `src/wowforever/classes/engines.py`
3. the eight class modules `rogue.py`, `hunter.py`, `warrior.py`, `paladin.py`, `priest.py`, `warlock.py`, `druid.py`, `shaman.py` (append a block at the end)

Do not edit the tests.

## Why
The duel model is for every class, but its side type is `MageSide`, with mage words in its fields (Thorns sits in `nova_dps`), and `pvp/duel.py` imports the mage rotation (#318, the review's candidate 3). #318 runs in four parts on one branch.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/classes/__init__.py b/src/wowforever/classes/__init__.py
index 2f85dc2..8ce702b 100644
--- a/src/wowforever/classes/__init__.py
+++ b/src/wowforever/classes/__init__.py
@@ -94,8 +94,13 @@ class ClassEngine(Protocol):
     def facts(self, stats: Any, cls: ClassData, ranks: Mapping[int, int]) -> dict[str, Any]:
         """What the rotation does, for the build description."""
 
+    def sides(self, stats: Any, spells: Sequence[SpellRank], cls: ClassData,
+              ranks: Mapping[int, int]) -> list[tuple[str | None, Any]]:
+        """The build's duel sides (pvp.duel.Side), each named by the filler it casts where it has a
+        choice (mage) or None; each duel scenario takes the best (#318)."""
 
-ENGINE_MEMBERS = ("playstyle", "output", "aoe", "facts")
+
+ENGINE_MEMBERS = ("playstyle", "output", "aoe", "facts", "sides")
 
 
 def engine(name: str) -> ClassEngine:
diff --git a/src/wowforever/classes/engines.py b/src/wowforever/classes/engines.py
index 882ead4..5ca0adb 100644
--- a/src/wowforever/classes/engines.py
+++ b/src/wowforever/classes/engines.py
@@ -95,3 +95,11 @@ def hybrid_facts(class_name: str, melee_trees: Sequence[str], melee_facts: Calla
             return melee_facts(stats.melee, cls, ranks)
         stats = stats.caster
     return caster_facts(class_name, plan, stats, cls, ranks)
+
+
+def one_side(class_name: str, stats: Any, spells: Sequence[SpellRank], cls: ClassData,
+             ranks: Mapping[int, int]) -> list[tuple[None, Any]]:
+    """A class with one way to duel: its class_pvp side, unnamed."""
+    from wowforever.pvp.class_pvp import class_side
+
+    return [(None, class_side(class_name, stats, spells, cls, ranks))]
diff --git a/src/wowforever/classes/rogue.py b/src/wowforever/classes/rogue.py
index 3cf5227..2267b04 100644
--- a/src/wowforever/classes/rogue.py
+++ b/src/wowforever/classes/rogue.py
@@ -182,3 +182,9 @@ def facts(stats, cls, ranks):
     r = rogue_rotation(stats, cls.spells, cls, ranks, Target(0, 0))
     return {"kind": "rogue", "builder": r.builder,
             "split": {"auto-attacks": r.white_dps / r.dps, "abilities and poisons": r.yellow_dps / r.dps}}
+
+
+def sides(stats, spells, cls, ranks):
+    from wowforever.classes.engines import one_side
+
+    return one_side("rogue", stats, spells, cls, ranks)
diff --git a/src/wowforever/classes/hunter.py b/src/wowforever/classes/hunter.py
index 14033a3..125ba13 100644
--- a/src/wowforever/classes/hunter.py
+++ b/src/wowforever/classes/hunter.py
@@ -164,3 +164,9 @@ def facts(stats, cls, ranks):
     r = hunter_rotation(stats, cls.spells, cls, ranks, Target(0, 0), pet=pet)
     split = {"pet": r.pet_dps / r.dps} if pet and r.dps else {}
     return {"kind": "hunter", "mode": r.mode, "pet": pet, "split": split}
+
+
+def sides(stats, spells, cls, ranks):
+    from wowforever.classes.engines import one_side
+
+    return one_side("hunter", stats, spells, cls, ranks)
diff --git a/src/wowforever/classes/warrior.py b/src/wowforever/classes/warrior.py
index 90efdaf..a01d540 100644
--- a/src/wowforever/classes/warrior.py
+++ b/src/wowforever/classes/warrior.py
@@ -149,3 +149,9 @@ def facts(stats, cls, ranks):
     r = warrior_rotation(stats, cls.spells, cls, ranks, Target(0, 0))
     return {"kind": "abilities", "abilities": list(r.abilities),
             "split": {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps}}
+
+
+def sides(stats, spells, cls, ranks):
+    from wowforever.classes.engines import one_side
+
+    return one_side("warrior", stats, spells, cls, ranks)
diff --git a/src/wowforever/classes/paladin.py b/src/wowforever/classes/paladin.py
index 1be9f75..76709ed 100644
--- a/src/wowforever/classes/paladin.py
+++ b/src/wowforever/classes/paladin.py
@@ -137,3 +137,9 @@ def facts(stats, cls, ranks):
     r = paladin_rotation(stats, cls.spells, cls, ranks, Target(0, 0))
     return {"kind": "abilities", "abilities": list(r.abilities),
             "split": {"auto-attacks": r.white_dps / r.dps, "Holy damage": r.holy_dps / r.dps}}
+
+
+def sides(stats, spells, cls, ranks):
+    from wowforever.classes.engines import one_side
+
+    return one_side("paladin", stats, spells, cls, ranks)
diff --git a/src/wowforever/classes/priest.py b/src/wowforever/classes/priest.py
index 2b17e03..1633dbe 100644
--- a/src/wowforever/classes/priest.py
+++ b/src/wowforever/classes/priest.py
@@ -157,3 +157,9 @@ def facts(stats, cls, ranks):
     from wowforever.classes.engines import caster_facts
 
     return caster_facts("priest", ROTATION, stats, cls, ranks)
+
+
+def sides(stats, spells, cls, ranks):
+    from wowforever.classes.engines import one_side
+
+    return one_side("priest", stats, spells, cls, ranks)
diff --git a/src/wowforever/classes/warlock.py b/src/wowforever/classes/warlock.py
index 46696ec..c1d5961 100644
--- a/src/wowforever/classes/warlock.py
+++ b/src/wowforever/classes/warlock.py
@@ -155,3 +155,9 @@ def facts(stats, cls, ranks):
     from wowforever.classes.engines import caster_facts
 
     return caster_facts("warlock", ROTATION, stats, cls, ranks)
+
+
+def sides(stats, spells, cls, ranks):
+    from wowforever.classes.engines import one_side
+
+    return one_side("warlock", stats, spells, cls, ranks)
diff --git a/src/wowforever/classes/druid.py b/src/wowforever/classes/druid.py
index e78df57..856abbf 100644
--- a/src/wowforever/classes/druid.py
+++ b/src/wowforever/classes/druid.py
@@ -218,3 +218,9 @@ def facts(stats, cls, ranks):
     from wowforever.classes.engines import hybrid_facts
 
     return hybrid_facts("druid", MELEE_TREES, _melee_facts, ROTATION, stats, cls, ranks)
+
+
+def sides(stats, spells, cls, ranks):
+    from wowforever.classes.engines import one_side
+
+    return one_side("druid", stats, spells, cls, ranks)
diff --git a/src/wowforever/classes/shaman.py b/src/wowforever/classes/shaman.py
index 3a38d22..b720366 100644
--- a/src/wowforever/classes/shaman.py
+++ b/src/wowforever/classes/shaman.py
@@ -176,3 +176,9 @@ def facts(stats, cls, ranks):
     from wowforever.classes.engines import hybrid_facts
 
     return hybrid_facts("shaman", MELEE_TREES, _melee_facts, ROTATION, stats, cls, ranks)
+
+
+def sides(stats, spells, cls, ranks):
+    from wowforever.classes.engines import one_side
+
+    return one_side("shaman", stats, spells, cls, ranks)
```

## Environment note
The package is already installed in `.venv` (editable). Part A (the renames) is done on this branch. The tests are already updated for the whole of #318, so tests that use `duel_side` or the mage's `sides` still fail after this part; parts C and D fix them. That is expected. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_class_engine.py -k "sides and not mage"`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
In `tests/test_class_engine.py`, `test_sides_name_the_filler_only_where_the_class_chooses_one` passes for the eight non-mage classes.
