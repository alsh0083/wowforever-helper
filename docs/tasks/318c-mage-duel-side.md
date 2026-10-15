# Task #318, part C: the mage builds its duel sides

Move the mage's side builder out of the generic duel model. This is a refactor, so no score and no build description may change. Edit only these files, in this order:
1. `src/wowforever/classes/mage.py`
2. `src/wowforever/pvp/duel.py`

Do not edit the tests.

## Why
The duel model is for every class, but its side type is `MageSide`, with mage words in its fields (Thorns sits in `nova_dps`), and `pvp/duel.py` imports the mage rotation (#318, the review's candidate 3). #318 runs in four parts on one branch.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/classes/mage.py b/src/wowforever/classes/mage.py
index 3a47cf5..6912bc9 100644
--- a/src/wowforever/classes/mage.py
+++ b/src/wowforever/classes/mage.py
@@ -242,13 +242,12 @@ def facts(stats, cls, ranks):
     """The spells the mage's scenarios pick at the build's level: questing, raid, AoE and caster PvP."""
     from wowforever.assumptions import Assumptions
     from wowforever.pvp.duel import best_scenario_scores, load_kits
-    from wowforever.scenarios import aoe_curve, default_params, questing, raid, usable_fillers
+    from wowforever.scenarios import aoe_curve, default_params, questing, raid
 
     assumptions = Assumptions.load()
     char = _character(stats, cls.spells, cls, ranks)
     level = stats.level
-    fillers = usable_fillers(char, default_params("questing", level).fillers, level, assumptions)
-    duels = best_scenario_scores(char, fillers, load_kits(level=level))
+    duels = best_scenario_scores(sides(stats, cls.spells, cls, ranks), load_kits(level=level))
     # "scenarios": which scored scenario each spell belongs to, so a description names only the
     # scenarios the build was scored in (a leveling build: questing)
     return {"kind": "mage", "scenarios": {"questing": "questing", "raid": "raid", "aoe": "aoe", "pvp": "wpvp_caster"},
@@ -256,3 +255,51 @@ def facts(stats, cls, ranks):
             "raid": raid(char, default_params("raid", level), assumptions).details["spell"],
             "aoe": aoe_curve(char, default_params("aoe", level), assumptions).details["aoe_spell"],
             "pvp": duels["wpvp_caster"]["spell"]}
+
+
+def duel_side(char, filler):
+    """The mage's duel side with one filler: short-fight rotation DPS (no sustained buffs) plus the
+    survival and control components, and Frost Nova's frozen hits against melee."""
+    from wowforever.assumptions import Assumptions
+    from wowforever.calc.pvp_axes import control, survival
+    from wowforever.classes.mage_rotation import frozen_hit_gain, rotation
+    from wowforever.pvp.duel import Side
+    from wowforever.scenarios import best_rank
+
+    s = survival(char, filler)
+    c = control(char, filler)
+    health = char.stats.health
+    assumptions = Assumptions.load()
+    nova = best_rank(char.spells, "Frost Nova", char.level)
+    melee_bonus_dps = 0.0
+    if nova is not None:
+        improved = next((t for t in char.cls.talents if t.name == "Improved Frost Nova"), None)
+        rank = char.ranks.get(improved.talent_id, 0) if improved else 0
+        cut = next((e.values[rank - 1] for e in improved.effects if e.kind == "cooldown"), 0.0) if rank else 0.0
+        cooldown = nova.cooldown + cut  # Improved Frost Nova's value is negative
+        if cooldown > 0:
+            melee_bonus_dps = frozen_hit_gain(char, filler, target_level=char.level,
+                                       assumptions=assumptions) / cooldown
+    return Side(
+        health=health,
+        dps=rotation(char, filler, target_level=char.level,
+                     assumptions=assumptions, sustained=False).dps,
+        absorb_per_min=s.components["barrier"] * health,
+        immunity_share=s.components["immunity"],
+        root=c.components["root"],
+        stun=c.components["stun"],
+        slow=c.components["slow"],
+        interrupt=c.components["interrupt"],
+        melee_bonus_dps=melee_bonus_dps,
+        root_targets=2 if nova is not None else 1,   # Frost Nova roots every nearby enemy (#287)
+    )
+
+
+def sides(stats, spells, cls, ranks):
+    """The mage's duel sides, one per usable filler: each duel scenario takes the best (#97)."""
+    from wowforever.assumptions import Assumptions
+    from wowforever.scenarios import default_params, usable_fillers
+
+    char = _character(stats, spells, cls, ranks)
+    fillers = usable_fillers(char, default_params("questing", stats.level).fillers, stats.level, Assumptions.load())
+    return [(filler.name, duel_side(char, filler)) for filler in fillers]
diff --git a/src/wowforever/pvp/duel.py b/src/wowforever/pvp/duel.py
index 5d0ba40..e8af5d2 100644
--- a/src/wowforever/pvp/duel.py
+++ b/src/wowforever/pvp/duel.py
@@ -16,11 +16,6 @@ from dataclasses import dataclass
 from pathlib import Path
 from typing import Any
 
-from wowforever.assumptions import Assumptions
-from wowforever.calc.pvp_axes import control, survival
-from wowforever.classes.mage_rotation import frozen_hit_gain, rotation
-from wowforever.schema import SpellRank
-from wowforever.scenarios import Character, best_rank
 
 CONFIG = Path(__file__).resolve().parents[3] / "config" / "duel.toml"
 OPPONENTS = Path(__file__).resolve().parents[3] / "config" / "opponents"
@@ -73,17 +68,18 @@ class Kit:
 
 @dataclass(frozen=True)
 class Side:
-    """The mage's side of a duel: health, DPS and control in seconds per minute."""
+    """One side of a duel, any class: health, DPS and control in seconds per minute. Class engines build
+    it (`sides`, #318); the mage's Ice Barrier, Ice Block and Frost Nova enter through the same fields."""
 
     health: float
     dps: float
-    absorb_per_min: float  # Ice Barrier absorb per minute
+    absorb_per_min: float  # absorb shields per minute (the mage's Ice Barrier)
     immunity_share: float  # share of the fight spent immune (Ice Block + Cold Snap)
     root: float
     stun: float
     slow: float  # uptime x strength, 0-1
     interrupt: float
-    melee_bonus_dps: float = 0.0  # extra DPS against melee: one frozen hit per Frost Nova (#97)
+    melee_bonus_dps: float = 0.0  # extra DPS against melee: Frost Nova's frozen hits (#97), Thorns (#265)
     physical_taken: float = 1.0  # physical damage taken vs the cloth that kit DPS assumes (#134)
     heal_hps: float = 0.0  # healing per second while casting heals (#265)
     heal_budget: float = 0.0  # mana-limited healing for the fight
@@ -361,45 +357,13 @@ def outnumbered_scores(side: Side, kits: Sequence[Kit]) -> dict[str, Any]:
     return {"score": sum(matchups.values()) / len(matchups) if matchups else 0.5, "matchups": matchups}
 
 
-def best_scenario_scores(char: Character, fillers: Sequence[SpellRank],
+def best_scenario_scores(sides: Sequence[tuple[str | None, Side]],
                          kits: Sequence[Kit]) -> dict[str, dict[str, Any]]:
-    """Per scenario, the result of the filler that scores best in it (ties: the earlier filler),
-    with that filler's name under "spell" (#97)."""
+    """Per scenario, the result of the side that scores best in it (ties: the earlier side), with that
+    side's name under "spell" (#97): a class engine's `sides` (#318), one per filler for the mage."""
     best: dict[str, dict[str, Any]] = {}
-    for filler in fillers:
-        for name, result in scenario_scores(mage_side(char, filler), kits).items():
+    for spell, side in sides:
+        for name, result in scenario_scores(side, kits).items():
             if name not in best or result["score"] > best[name]["score"]:
-                best[name] = {**result, "spell": filler.name}
+                best[name] = {**result, "spell": spell}
     return best
-
-
-def mage_side(char: Character, filler: SpellRank) -> Side:
-    """The mage's duel side from a build: short-fight rotation DPS (no sustained buffs)
-    plus the survival and control components."""
-    s = survival(char, filler)
-    c = control(char, filler)
-    health = char.stats.health
-    assumptions = Assumptions.load()
-    nova = best_rank(char.spells, "Frost Nova", char.level)
-    melee_bonus_dps = 0.0
-    if nova is not None:
-        improved = next((t for t in char.cls.talents if t.name == "Improved Frost Nova"), None)
-        rank = char.ranks.get(improved.talent_id, 0) if improved else 0
-        cut = next((e.values[rank - 1] for e in improved.effects if e.kind == "cooldown"), 0.0) if rank else 0.0
-        cooldown = nova.cooldown + cut  # Improved Frost Nova's value is negative
-        if cooldown > 0:
-            melee_bonus_dps = frozen_hit_gain(char, filler, target_level=char.level,
-                                       assumptions=assumptions) / cooldown
-    return Side(
-        health=health,
-        dps=rotation(char, filler, target_level=char.level,
-                     assumptions=assumptions, sustained=False).dps,
-        absorb_per_min=s.components["barrier"] * health,
-        immunity_share=s.components["immunity"],
-        root=c.components["root"],
-        stun=c.components["stun"],
-        slow=c.components["slow"],
-        interrupt=c.components["interrupt"],
-        melee_bonus_dps=melee_bonus_dps,
-        root_targets=2 if nova is not None else 1,   # Frost Nova roots every nearby enemy (#287)
-    )
```

## Environment note
The package is already installed in `.venv` (editable). Parts A and B are done on this branch. After this part `report.py` and `focus.py` still import the old `mage_side` / call the old `best_scenario_scores` signature, so tests that import them fail until part D. That is expected. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_class_engine.py tests/test_duel.py tests/test_duel_filler.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`tests/test_duel.py`, `tests/test_duel_filler.py` and `tests/test_class_engine.py` pass.
