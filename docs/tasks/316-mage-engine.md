# Task #316: the mage implements ClassEngine

Make `tests/test_class_engine.py` pass without breaking the rest of the suite. This is a refactor, so no score and no build description may change. Edit only these files, in this order:
1. `src/wowforever/melee_scenarios.py`
2. `src/wowforever/classes/mage.py` (append a block at the end)
3. `src/wowforever/describe.py`
4. `src/wowforever/group.py`

Do not edit the tests.

## Why
The mage was the last scored class without a `ClassEngine` (docs/planning/2026-10-14-class-engine.md, mage slices). Its adapter sits next to its own scenario pipeline (`scenarios.py`): `output` picks the filler like the caster engine and reports it in `Output.spell`, and `facts` names the spells its scenarios pick. Report paths don't change until #317.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/classes/mage.py b/src/wowforever/classes/mage.py
index b2ba49c..3a47cf5 100644
--- a/src/wowforever/classes/mage.py
+++ b/src/wowforever/classes/mage.py
@@ -176,3 +176,83 @@ ENGINE = True
 
 # Mage skill lines in SkillLineAbility: Frost, Fire, Arcane.
 SKILL_LINES = (6, 8, 237)
+
+
+# --- class engine (#316): this module is the mage's ClassEngine ---------------------------------------
+# The mage keeps its own scenario pipeline (scenarios.py) until #317; these adapters let every caller
+# reach the mage through the same interface as the other classes.
+
+def _character(stats, spells, cls, ranks):
+    from wowforever.scenarios import Character
+
+    return Character(stats.level, stats, spells, cls, dict(ranks))
+
+
+def playstyle(cls, ranks) -> str:
+    return "caster"
+
+
+def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None):
+    """The mage rotation with the filler that does the most damage per second, or with
+    `drink_mana_per_second` (questing) the most per second of casting plus drinking, as the caster
+    engine picks. The chosen filler is `Output.spell`."""
+    from wowforever.assumptions import Assumptions
+    from wowforever.classes.mage_rotation import rotation
+    from wowforever.melee_scenarios import Output
+    from wowforever.scenarios import combat_regen, default_params, usable_fillers
+
+    assumptions = Assumptions.load()
+    char = _character(stats, spells, cls, ranks)
+    target_level = stats.level + target.level_diff
+    best = None
+    for filler in usable_fillers(char, default_params("questing", stats.level).fillers, target_level, assumptions):
+        rot = rotation(char, filler, target_level=target_level, assumptions=assumptions, sustained=False)
+        if rot.dps <= 0:
+            continue
+        value = rot.dps
+        if drink_mana_per_second:
+            value = rot.dps / (1 + rot.mana_per_second / drink_mana_per_second)
+        if best is None or value > best[0]:
+            best = (value, filler, rot)
+    if best is None:
+        raise ValueError(f"no mage filler available at level {stats.level}")
+    _, filler, rot = best
+    # once dry, the mage keeps casting at the rate combat regen pays for (as scenarios.raid's fallback)
+    income = combat_regen(char, default_params("raid", stats.level))
+    fallback = rot.dps * min(1.0, income / rot.mana_per_second) if rot.mana_per_second > 0 else rot.dps
+    return Output(rot.dps, rot.mana_per_second, fallback, ranged=True, spell=filler.name)
+
+
+def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
+    """Seconds to clear `pack` mobs with the mage's best AoE spell (scenarios.aoe_curve's model)."""
+    from wowforever.assumptions import Assumptions
+    from wowforever.scenarios import _best_of, _cast, default_params
+
+    assumptions = Assumptions.load()
+    char = _character(stats, spells, cls, ranks)
+    spell = _best_of(char, default_params("aoe", stats.level).aoe_spells, char.level, assumptions, "AoE spell")
+    ev, cast, _ = _cast(char, spell, char.level, assumptions)
+    per_mob = ev / cast
+    if assumptions["aoe_target_cap"] == "soft_4":
+        per_mob *= min(pack, 4) / pack
+    return mob_hp / per_mob, spell.name
+
+
+def facts(stats, cls, ranks):
+    """The spells the mage's scenarios pick at the build's level: questing, raid, AoE and caster PvP."""
+    from wowforever.assumptions import Assumptions
+    from wowforever.pvp.duel import best_scenario_scores, load_kits
+    from wowforever.scenarios import aoe_curve, default_params, questing, raid, usable_fillers
+
+    assumptions = Assumptions.load()
+    char = _character(stats, cls.spells, cls, ranks)
+    level = stats.level
+    fillers = usable_fillers(char, default_params("questing", level).fillers, level, assumptions)
+    duels = best_scenario_scores(char, fillers, load_kits(level=level))
+    # "scenarios": which scored scenario each spell belongs to, so a description names only the
+    # scenarios the build was scored in (a leveling build: questing)
+    return {"kind": "mage", "scenarios": {"questing": "questing", "raid": "raid", "aoe": "aoe", "pvp": "wpvp_caster"},
+            "questing": questing(char, default_params("questing", level), assumptions).details["spell"],
+            "raid": raid(char, default_params("raid", level), assumptions).details["spell"],
+            "aoe": aoe_curve(char, default_params("aoe", level), assumptions).details["aoe_spell"],
+            "pvp": duels["wpvp_caster"]["spell"]}
diff --git a/src/wowforever/describe.py b/src/wowforever/describe.py
index d40d122..e519e9f 100644
--- a/src/wowforever/describe.py
+++ b/src/wowforever/describe.py
@@ -190,14 +190,12 @@ def rotation_facts(class_name: str, cls: ClassData, ranks: Mapping[int, int], st
     """What the class engine's rotation does at level 60 against a level-60 target."""
     from .classes import engine
 
-    if class_name == "mage":
-        def cell(s: str) -> str | None:
-            by_level = scores.get(s) or {}
-            return (by_level.get("60") or by_level.get(60) or {}).get("spell")
-
-        return {"kind": "mage", "questing": cell("questing"), "raid": cell("raid"), "aoe": cell("aoe"),
-                "pvp": cell("wpvp_caster")}
-    return engine(class_name).facts(stats, cls, ranks)
+    facts = engine(class_name).facts(stats, cls, ranks)
+    for key, scenario in facts.pop("scenarios", {}).items():
+        by_level = scores.get(scenario) or {}
+        if not (by_level.get("60") or by_level.get(60)):
+            facts[key] = None            # not scored at 60 (a leveling build): don't name its spell
+    return facts
 
 
 def _buff_names() -> dict[str, str]:
diff --git a/src/wowforever/group.py b/src/wowforever/group.py
index a5fde2d..03a6699 100644
--- a/src/wowforever/group.py
+++ b/src/wowforever/group.py
@@ -445,8 +445,6 @@ def _kind_for(class_name: str, stats, cls, ranks) -> str:
     """How the build fights, which picks its party's buff preferences: melee, ranged or caster."""
     from wowforever.classes import engine
 
-    if class_name == "mage":               # until the mage has its class engine (#316)
-        return "caster"
     return engine(class_name).playstyle(cls, ranks)
 
 
diff --git a/src/wowforever/melee_scenarios.py b/src/wowforever/melee_scenarios.py
index fc6a005..5862bf3 100644
--- a/src/wowforever/melee_scenarios.py
+++ b/src/wowforever/melee_scenarios.py
@@ -67,6 +67,7 @@ class Output:
     aoe: tuple[str, ...] = ()   # abilities that hit several mobs of a pack (#262)
     pet: bool = False           # a pet fights alongside (and tanks while questing)
     ranged: bool = False        # the rotation fights from range
+    spell: str | None = None    # the filler the rotation chose, where it chooses one (mage, #316)
 
 
 def _config() -> dict:
```

## Environment note
The package is already installed in `.venv` (editable). Before you start, `test_mage_implements_the_class_engine_next_to_its_scenarios` fails with `ValueError: no class engine for 'mage'`. That is the expected failure. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_class_engine.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
