# Task #313, part B: rotation_output goes

Make the whole suite pass. This is a refactor, so no score and no build description may change. Edit only these files, in this order:
1. `src/wowforever/melee_scenarios.py`
2. `src/wowforever/pvp/class_pvp.py`
3. `src/wowforever/pvp/kit_stats.py`

Do not edit the tests.

## Why
The last hybrid checks and `rotation_output` callers move to `engine(name)`: `.output(...)` and `.playstyle(...)` (#313, in two runs on one branch).

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/melee_scenarios.py b/src/wowforever/melee_scenarios.py
index e3f7b81..fc6a005 100644
--- a/src/wowforever/melee_scenarios.py
+++ b/src/wowforever/melee_scenarios.py
@@ -15,6 +15,7 @@ from dataclasses import dataclass, fields
 from pathlib import Path
 from typing import Any
 
+from wowforever.classes import engine
 from wowforever.melee_stats import MeleeStats
 from wowforever.physical import Target
 from wowforever.scenarios import _anchor_at, default_params
@@ -120,9 +121,9 @@ def stat_table(class_name: str):
 def build_stats(class_name: str, stats, cls: ClassData, ranks: Mapping[int, int]):
     """The stats row a build fights with: a hybrid's melee row for its melee builds, else `stats`."""
     if isinstance(stats, HybridStats):
-        from wowforever.classes import class_module
+        from wowforever.classes import engine
 
-        return stats.melee if main_tree(cls, ranks) in class_module(class_name).MELEE_TREES else stats.caster
+        return stats.melee if engine(class_name).playstyle(cls, ranks) == "melee" else stats.caster
     return stats
 
 
@@ -132,26 +133,13 @@ def main_tree(cls: ClassData, ranks: Mapping[int, int]) -> str:
     return max(points, key=points.get)
 
 
-def rotation_output(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
-                    ranks: Mapping[int, int], target: Target, *, drink_mana_per_second: float | None = None,
-                    melee: bool | None = None, pack: int = 1) -> Output:
-    """The class rotation's DPS, mana use and out-of-mana fallback against `target`. For a hybrid,
-    `melee` fixes the playstyle (a Feral leveling path is a cat even while its points sit in Balance);
-    by default it follows the tree with most points. `pack` > 1 sums damage over that many mobs for
-    classes whose AoE abilities are modeled (#262); a cat druid stays single target."""
-    from wowforever.classes import engine
-
-    return engine(class_name).output(stats, spells, cls, ranks, target, pack=pack,
-                                     drink_mana_per_second=drink_mana_per_second, melee=melee)
-
-
 def questing(class_name: str, stats: MeleeStats, spells, cls, ranks, *, melee: bool | None = None) -> float:
     """Kills per hour against same-level mobs: kill time + recovery downtime + travel."""
     level = stats.level
     q = default_params("questing", level)
     armor, mob_dps, eat = _anchor_at(_config()["questing"]["anchors"], level)
-    out = rotation_output(class_name, stats, spells, cls, ranks, Target(0, armor),
-                          drink_mana_per_second=q.drink_mana_per_second, melee=melee)
+    out = engine(class_name).output(stats, spells, cls, ranks, Target(0, armor),
+                                    drink_mana_per_second=q.drink_mana_per_second, melee=melee)
     kill = q.mob_hp / out.dps
     downtime = 0.0 if out.pet else mob_dps * kill / eat     # a pet tanks while the hunter shoots
     if out.mana_per_second > 0:
@@ -163,15 +151,14 @@ def dungeon(class_name: str, stats: MeleeStats, spells, cls, ranks) -> float:
     """DPS on a level+2 dungeon pull with tank debuffs (one minute; mana isn't limiting)."""
     d = _config()["dungeon"]
     armor = _anchor_at(_config()["questing"]["anchors"], stats.level)[0] * d["armor_share_of_questing"]
-    return rotation_output(class_name, stats, spells, cls, ranks,
-                           Target(d["target_level_offset"], armor)).dps
+    return engine(class_name).output(stats, spells, cls, ranks, Target(d["target_level_offset"], armor)).dps
 
 
 def raid(class_name: str, stats: MeleeStats, spells, cls, ranks) -> float:
     """Sustained DPS against a debuffed boss over the mage's fight-length mix; hunters spend the
     same mana budget (pool, Mana Ruby, potions and runes, Blessing of Wisdom), then Auto Shot."""
     r = _config()["raid"]
-    out = rotation_output(class_name, stats, spells, cls, ranks, Target(r["target_level_offset"], r["armor"]))
+    out = engine(class_name).output(stats, spells, cls, ranks, Target(r["target_level_offset"], r["armor"]))
     p = default_params("raid", stats.level)
     drain = out.mana_per_second - p.mana_per_second
     lengths = p.fight_lengths or ((p.fight_seconds, 1.0),)
@@ -191,10 +178,8 @@ def raid(class_name: str, stats: MeleeStats, spells, cls, ranks) -> float:
 def aoe(class_name: str, stats: MeleeStats, spells, cls, ranks) -> tuple[float, str]:
     """Seconds to clear a pack of same-level questing mobs (#263) and the AoE spell used, or "single
     target". Spell-engine classes (and a hybrid's caster builds) mix their AoE spells into the rotation
-    (caster.aoe_pull, #260); the others run their rotation against the pack (rotation_output's `pack`,
+    (caster.aoe_pull, #260); the others run their rotation against the pack (the engine's `pack`,
     #262), single target where their AoE abilities aren't modeled yet."""
-    from wowforever.classes import engine
-
     pack = _config()["aoe"]["pack"]
     mob_hp = default_params("aoe", stats.level).mob_hp
     armor = _anchor_at(_config()["questing"]["anchors"], stats.level)[0]
diff --git a/src/wowforever/pvp/class_pvp.py b/src/wowforever/pvp/class_pvp.py
index ff522b8..f7fbeb9 100644
--- a/src/wowforever/pvp/class_pvp.py
+++ b/src/wowforever/pvp/class_pvp.py
@@ -20,7 +20,8 @@ from pathlib import Path
 from wowforever.assumptions import Assumptions
 from wowforever.calc.ev import BASE_CRIT_BONUS_PCT, GCD_SECONDS
 from wowforever.focus import PVP_SCENARIOS
-from wowforever.melee_scenarios import build_stats, rotation_output
+from wowforever.classes import engine
+from wowforever.melee_scenarios import build_stats
 from wowforever.melee_stats import MeleeStats
 from wowforever.physical import Target, armor_factor
 from wowforever.pvp.duel import Control, Kit, MageSide, lockout_seconds, outnumbered_scores, scenario_scores
@@ -164,7 +165,7 @@ def class_side(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank],
     wide = [ctrl for ctrl, c in zip(controls, entries)
             if (spell := best_rank(spells, c["name"], stats.level)) is not None and spell.max_targets > 1]
     wide_locks = lockout_seconds(wide, cfg.get("energy_per_minute", 0.0))
-    output = rotation_output(class_name, stats, spells, cls, ranks, Target(0, raw["player_armor"]))
+    output = engine(class_name).output(stats, spells, cls, ranks, Target(0, raw["player_armor"]))
     slow = cfg.get("slow", 0.0)
     if "slow_ranged" in cfg:                    # a slow that depends on the range it fights at (hunter)
         slow = cfg["slow_ranged"] if output.ranged else cfg["slow_melee"]
diff --git a/src/wowforever/pvp/kit_stats.py b/src/wowforever/pvp/kit_stats.py
index 3a0e702..5756225 100644
--- a/src/wowforever/pvp/kit_stats.py
+++ b/src/wowforever/pvp/kit_stats.py
@@ -14,7 +14,8 @@ from pathlib import Path
 from wowforever.builds import load_builds
 from wowforever.classes import class_module
 from wowforever.effects import attach_effects
-from wowforever.melee_scenarios import build_stats, rotation_output, stat_table
+from wowforever.classes import engine
+from wowforever.melee_scenarios import build_stats, stat_table
 from wowforever.physical import Target
 from wowforever.schema import Dataset, latest_dataset_path
 from wowforever.toml_cache import load_toml
@@ -50,7 +51,7 @@ def engine_at_60(kit_id: str) -> tuple[float, float]:
     build = {b.id: b for b in load_builds(class_name=class_name)}[KIT_BUILDS[kit_id]]
     ranks = build.final_ids(cls)
     cloth_armor = load_toml(ROOT / "config" / "pvp_self.toml")["cloth_armor"]
-    dps = rotation_output(class_name, stats, cls.spells, cls, ranks, Target(0, cloth_armor)).dps
+    dps = engine(class_name).output(stats, cls.spells, cls, ranks, Target(0, cloth_armor)).dps
     return build_stats(class_name, stats, cls, ranks).health, dps
 
 
@@ -79,5 +80,5 @@ def engine_at(kit_id: str, level: int) -> tuple[float, float]:
     build = {b.id: b for b in load_builds(class_name=class_name)}[KIT_BUILDS[kit_id]]
     ranks = kit_ranks_at(build, cls, level)
     cloth_armor = load_toml(ROOT / "config" / "pvp_self.toml")["cloth_armor"]
-    dps = rotation_output(class_name, stats, cls.spells, cls, ranks, Target(0, cloth_armor)).dps
+    dps = engine(class_name).output(stats, cls.spells, cls, ranks, Target(0, cloth_armor)).dps
     return build_stats(class_name, stats, cls, ranks).health, dps
```

## Environment note
The package is already installed in `.venv` (editable). Part A (group, report) is already done on this branch. Before you start, `test_scenarios_ask_the_engine_with_no_class_chain` fails because `melee_scenarios.rotation_output` still exists. That is the expected failure. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_class_engine.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
