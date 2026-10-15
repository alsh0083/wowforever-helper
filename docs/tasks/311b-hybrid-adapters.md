# Task #311, part B: hybrid adapters (druid, shaman) and the dispatch collapse

Make the whole suite pass. This is a refactor, so no score may change. Edit only these files, in this order:
1. `src/wowforever/classes/druid.py`
2. `src/wowforever/classes/shaman.py`
3. `src/wowforever/melee_scenarios.py`

Do not edit the tests.

## Why
The last four scored classes (priest, warlock, druid, shaman) become `ClassEngine`s, so `melee_scenarios.rotation_output` and `melee_scenarios.aoe` stop dispatching on the class. #311 runs in two parts on one branch; this is part B.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/classes/druid.py b/src/wowforever/classes/druid.py
index 12fcf6b..e239d46 100644
--- a/src/wowforever/classes/druid.py
+++ b/src/wowforever/classes/druid.py
@@ -171,3 +171,36 @@ CAVEAT = ("Balance (#166): Moonfire and Insect Swarm kept up, then Starfire or W
           "Nature's Grace and Omen of Clarity aren't modeled. Feral cat (#175): paw swings and a Shred or Claw to "
           "Ferocious Bite energy cycle on the melee engine, Classic paw damage; Rake and Rip bleeds, Tiger's Fury and "
           "powershifting aren't modeled. The bear tank and Restoration stay unscored. Base stats are estimates.")
+
+
+# --- class engine (#311): this module is the druid's ClassEngine ------------------------------------
+from wowforever.classes.engines import facts_later as facts  # noqa: E402
+
+
+def playstyle(cls, ranks) -> str:
+    from wowforever.classes.engines import melee_build
+
+    return "melee" if melee_build(MELEE_TREES, cls, ranks) else "caster"
+
+
+def _melee_output(stats, spells, cls, ranks, target, *, pack=1):
+    # a cat stays single target (#262)
+    from wowforever.classes.druid_rotation import cat_rotation
+    from wowforever.melee_scenarios import Output
+
+    r = cat_rotation(stats, spells, cls, ranks, target)
+    return Output(r.dps, 0.0, r.dps)
+
+
+def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None):
+    from wowforever.classes.engines import hybrid_output
+
+    return hybrid_output("druid", MELEE_TREES, _melee_output, stats, spells, cls, ranks, target, pack=pack,
+                         drink_mana_per_second=drink_mana_per_second, melee=melee)
+
+
+def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
+    from wowforever.classes.engines import hybrid_aoe
+
+    return hybrid_aoe("druid", MELEE_TREES, output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp,
+                      armor=armor)
diff --git a/src/wowforever/classes/shaman.py b/src/wowforever/classes/shaman.py
index 2344f48..db43970 100644
--- a/src/wowforever/classes/shaman.py
+++ b/src/wowforever/classes/shaman.py
@@ -130,3 +130,35 @@ CAVEAT = ("Elemental (#167): Flame Shock kept up, Lava Burst and Chain Lightning
           "attack power) and Flurry, Stormstrike and Earth Shock on cooldown on the melee engine; Stormstrike's "
           "debuff, Maelstrom Weapon, totems and Enhancement's mana aren't modeled. Restoration stays unscored. "
           "Base stats are estimates.")
+
+
+# --- class engine (#311): this module is the shaman's ClassEngine ------------------------------------
+from wowforever.classes.engines import facts_later as facts  # noqa: E402
+
+
+def playstyle(cls, ranks) -> str:
+    from wowforever.classes.engines import melee_build
+
+    return "melee" if melee_build(MELEE_TREES, cls, ranks) else "caster"
+
+
+def _melee_output(stats, spells, cls, ranks, target, *, pack=1):
+    from wowforever.classes.shaman_rotation import enhancement_rotation
+    from wowforever.melee_scenarios import Output
+
+    r = enhancement_rotation(stats, spells, cls, ranks, target, pack=pack)
+    return Output(r.dps, 0.0, r.dps, r.aoe)
+
+
+def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None):
+    from wowforever.classes.engines import hybrid_output
+
+    return hybrid_output("shaman", MELEE_TREES, _melee_output, stats, spells, cls, ranks, target, pack=pack,
+                         drink_mana_per_second=drink_mana_per_second, melee=melee)
+
+
+def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
+    from wowforever.classes.engines import hybrid_aoe
+
+    return hybrid_aoe("shaman", MELEE_TREES, output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp,
+                      armor=armor)
diff --git a/src/wowforever/melee_scenarios.py b/src/wowforever/melee_scenarios.py
index ccce7a6..e3f7b81 100644
--- a/src/wowforever/melee_scenarios.py
+++ b/src/wowforever/melee_scenarios.py
@@ -139,33 +139,10 @@ def rotation_output(class_name: str, stats: MeleeStats, spells: Sequence[SpellRa
     `melee` fixes the playstyle (a Feral leveling path is a cat even while its points sit in Balance);
     by default it follows the tree with most points. `pack` > 1 sums damage over that many mobs for
     classes whose AoE abilities are modeled (#262); a cat druid stays single target."""
-    from wowforever.classes import class_module
-
-    module = class_module(class_name)
-    if isinstance(stats, HybridStats):
-        if melee if melee is not None else main_tree(cls, ranks) in module.MELEE_TREES:
-            if class_name == "druid":
-                from wowforever.classes.druid_rotation import cat_rotation
-
-                r = cat_rotation(stats.melee, spells, cls, ranks, target)
-            else:
-                from wowforever.classes.shaman_rotation import enhancement_rotation
-
-                r = enhancement_rotation(stats.melee, spells, cls, ranks, target, pack=pack)
-            return Output(r.dps, 0.0, r.dps, getattr(r, "aoe", ()))
-        stats = stats.caster
-    if getattr(module, "ENGINE", None) == "spell":
-        from wowforever.caster import caster_rotation
-
-        r = caster_rotation(class_name, stats, spells, cls, ranks, target, drink_mana_per_second=drink_mana_per_second)
-        gross = r.mana_per_second + r.regen_per_second
-        # once dry, a caster keeps casting at the rate its regen pays for
-        return Output(r.dps, r.mana_per_second, r.dps * min(1.0, r.regen_per_second / gross) if gross > 0 else r.dps)
-    if class_name in ("rogue", "warrior", "paladin", "hunter"):
-        from wowforever.classes import engine
+    from wowforever.classes import engine
 
-        return engine(class_name).output(stats, spells, cls, ranks, target, pack=pack)
-    raise ValueError(f"no melee rotation for {class_name!r}")
+    return engine(class_name).output(stats, spells, cls, ranks, target, pack=pack,
+                                     drink_mana_per_second=drink_mana_per_second, melee=melee)
 
 
 def questing(class_name: str, stats: MeleeStats, spells, cls, ranks, *, melee: bool | None = None) -> float:
@@ -216,22 +193,12 @@ def aoe(class_name: str, stats: MeleeStats, spells, cls, ranks) -> tuple[float,
     target". Spell-engine classes (and a hybrid's caster builds) mix their AoE spells into the rotation
     (caster.aoe_pull, #260); the others run their rotation against the pack (rotation_output's `pack`,
     #262), single target where their AoE abilities aren't modeled yet."""
-    from wowforever.classes import class_module
+    from wowforever.classes import engine
 
-    module = class_module(class_name)
     pack = _config()["aoe"]["pack"]
     mob_hp = default_params("aoe", stats.level).mob_hp
-    row = stats if getattr(module, "ENGINE", None) == "spell" else None
-    if isinstance(stats, HybridStats):
-        row = None if main_tree(cls, ranks) in module.MELEE_TREES else stats.caster
-    if row is not None:
-        from wowforever.caster import aoe_pull
-
-        pull = aoe_pull(class_name, row, spells, cls, ranks, pack, mob_hp)
-        return pull.seconds, pull.spell
     armor = _anchor_at(_config()["questing"]["anchors"], stats.level)[0]
-    out = rotation_output(class_name, stats, spells, cls, ranks, Target(0, armor), pack=pack)
-    return pack * mob_hp / out.dps, ", ".join(out.aoe) or "single target"
+    return engine(class_name).aoe(stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)
 
 
 def pve_score(class_name: str, stats_at_max: MeleeStats, spells, cls, ranks) -> float:
```

## Environment note
The package is already installed in `.venv` (editable). Part A (priest, warlock, `classes/engines.py`) is already done on this branch. Before you start, `test_every_scored_class_but_mage_has_an_engine` fails with `ValueError: no class engine for 'druid'`. That's the expected failure. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_class_engine.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
