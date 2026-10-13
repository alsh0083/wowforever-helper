# Task #262 (paladin slice): Consecration against a pack

Make `tests/test_paladin_aoe.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/classes/paladin_rotation.py` and `src/wowforever/melee_scenarios.py`. The test docstring has the rule. `tests/test_aoe_score.py`'s single-target case now uses a cat druid, since paladins get AoE here.

## Why
#295 imports Consecration's tick damage correctly (312 over 8 s at rank 5). Retribution paladins still clear a pack one mob at a time, but Consecration hits every mob.

## Change
Make exactly the changes in this diff (`-` lines go, `+` lines come, the rest is context). Turn it into `tools/apply_patch.py` hunks: same files, same order, context copied from the files.

```diff
diff --git a/src/wowforever/classes/paladin_rotation.py b/src/wowforever/classes/paladin_rotation.py
index 10ca722..42b4190 100644
--- a/src/wowforever/classes/paladin_rotation.py
+++ b/src/wowforever/classes/paladin_rotation.py
@@ -5,9 +5,12 @@ Seal of Command and Judgement are Holy damage, so armor doesn't reduce them; the
 melee table's miss and crit. Constants that the client data doesn't carry (proc rate, Judgement of
 Command's damage) are Classic values in config/paladin.toml.
 
-Not modeled yet: Consecration, Exorcism and Hammer of Wrath (target or health limits), Vindication's
-attack power, Twist of Light's echo, Champion of the Light's spell power, and mana (Retribution's
-seal and strike costs are small next to its pool).
+Against a pack (`pack` > 1, AoE pulls #262) Consecration is kept down, hitting every mob for its base
+tick damage (the melee row carries no spell power; its ticks don't roll the combat table).
+
+Not modeled yet: Consecration against one mob, Exorcism and Hammer of Wrath (target or health
+limits), Vindication's attack power, Twist of Light's echo, Champion of the Light's spell power, and
+mana (Retribution's seal and strike costs are small next to its pool; Consecration's aren't).
 """
 
 from __future__ import annotations
@@ -31,11 +34,13 @@ class PaladinRotation:
     white_dps: float
     holy_dps: float
     abilities: tuple[str, ...]
+    aoe: tuple[str, ...] = ()   # abilities that hit more than one mob of the pack (#262)
 
 
 def paladin_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
-                     ranks: Mapping[int, int], target: Target) -> PaladinRotation:
-    """Sustained DPS against `target` with the paladin's talents `ranks`."""
+                     ranks: Mapping[int, int], target: Target, *, pack: int = 1) -> PaladinRotation:
+    """Sustained DPS against `target` with the paladin's talents `ranks`; with `pack` > 1, the damage
+    summed over a pack of that many such mobs (#262)."""
     c = load_toml(CONFIG)
     by_name = {t.name: t for t in cls.talents}
 
@@ -86,4 +91,12 @@ def paladin_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassD
         holy += yellow_attack(base, attacker, holy_target, crit_bonus=total("crit_chance", "Holy Strike"),
                               damage_pct=all_pct + total("damage_pct", "Holy Strike")) / strike.cooldown
         used.append("Holy Strike")
-    return PaladinRotation(dps=white + holy, white_dps=white, holy_dps=holy, abilities=tuple(used))
+    aoe: tuple[str, ...] = ()
+    consecration = best_rank(spells, "Consecration", stats.level) if pack > 1 else None
+    if consecration is not None and consecration.duration > 0 and consecration.periodic_damage > 0:
+        period = max(consecration.duration, consecration.cooldown)
+        holy += (consecration.periodic_damage * (1 + (all_pct + total("damage_pct", "Consecration")) / 100)
+                 * pack / period)
+        used.append("Consecration")
+        aoe = ("Consecration",)
+    return PaladinRotation(dps=white + holy, white_dps=white, holy_dps=holy, abilities=tuple(used), aoe=aoe)
diff --git a/src/wowforever/melee_scenarios.py b/src/wowforever/melee_scenarios.py
index 9369e34..ab67c3c 100644
--- a/src/wowforever/melee_scenarios.py
+++ b/src/wowforever/melee_scenarios.py
@@ -141,8 +141,7 @@ def rotation_output(class_name: str, stats: MeleeStats, spells: Sequence[SpellRa
     """The class rotation's DPS, mana use and out-of-mana fallback against `target`. For a hybrid,
     `melee` fixes the playstyle (a Feral leveling path is a cat even while its points sit in Balance);
     by default it follows the tree with most points. `pack` > 1 sums damage over that many mobs for
-    classes whose AoE abilities are modeled (warrior, rogue, hunter and Enhancement shaman, #262); the
-    others stay single target."""
+    classes whose AoE abilities are modeled (#262); a cat druid stays single target."""
     from wowforever.classes import class_module
 
     module = class_module(class_name)
@@ -178,8 +177,8 @@ def rotation_output(class_name: str, stats: MeleeStats, spells: Sequence[SpellRa
     if class_name == "paladin":
         from wowforever.classes.paladin_rotation import paladin_rotation
 
-        r = paladin_rotation(stats, spells, cls, ranks, target)
-        return Output(r.dps, 0.0, r.dps)
+        r = paladin_rotation(stats, spells, cls, ranks, target, pack=pack)
+        return Output(r.dps, 0.0, r.dps, r.aoe)
     if class_name == "warrior":
         from wowforever.classes.warrior_rotation import warrior_rotation
 
```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_paladin_aoe.py` fails with `TypeError` (`pack` is not an argument of `paladin_rotation`), and one test in `tests/test_aoe_score.py` may fail too. That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), one file at a time, with each file's hunks in file order.

## Done when
`.venv/Scripts/python -m pytest tests/test_paladin_aoe.py tests/test_aoe_score.py tests/test_paladin_engine.py` passes (skip any file that doesn't exist), and so does `.venv/Scripts/python -m pytest -m "not slow"`. Do not run the slow tests.
