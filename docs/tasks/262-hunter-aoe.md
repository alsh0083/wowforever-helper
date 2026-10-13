# Task #262 (hunter slice): Multi-Shot, Volley and Explosive Trap against a pack

Make `tests/test_hunter_aoe.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `config/hunter.toml`, `src/wowforever/classes/hunter_rotation.py` and `src/wowforever/melee_scenarios.py`. The test docstring has the rules.

## Why
The warrior, rogue and shaman slices of #262 gave their rotations a `pack` argument. Hunters still clear a pack one mob at a time. #268 put the trap damage on Explosive Trap, so hunters can now use Multi-Shot, Volley and Explosive Trap against a pack.

## Change
Make exactly the changes in this diff (`-` lines go, `+` lines come, the rest is context). Turn it into `tools/apply_patch.py` hunks: same files, same order, context copied from the files.

```diff
diff --git a/config/hunter.toml b/config/hunter.toml
index c9c9e64..33eadeb 100644
--- a/config/hunter.toml
+++ b/config/hunter.toml
@@ -11,3 +11,7 @@ trueshot_aura_rap = 30.0
 pet_dps_per_level = 1.2
 # Bestial Wrath: +50% pet damage for 18 s every 2 min (rank text; cooldown Classic)
 bestial_wrath = { bonus_pct = 50.0, duration = 18.0, cooldown = 120.0 }
+
+# AoE pulls (#262): Multi-Shot hits this many targets (Classic; Forever's data has no target count).
+# Volley and Explosive Trap hit every mob of the pack.
+multi_shot_targets = 3
diff --git a/src/wowforever/classes/hunter_rotation.py b/src/wowforever/classes/hunter_rotation.py
index 792d4e4..2fa9d6c 100644
--- a/src/wowforever/classes/hunter_rotation.py
+++ b/src/wowforever/classes/hunter_rotation.py
@@ -5,6 +5,10 @@ estimated pet for Beast Mastery. The rotation reports the better of ranged and m
 
 Pinned by tests/test_hunter_rotation.py; constants in config/hunter.toml.
 
+Against a pack (`pack` > 1, AoE pulls #262): Multi-Shot hits up to config multi_shot_targets mobs,
+the ranged hunter channels Volley instead when that does more, and Explosive Trap goes out on
+cooldown in either mode, hitting every mob.
+
 Not modeled yet: Rapid Killing's cooldown cut, Deadly Aspects procs, Expose Prey, hawk damage,
 Resourcefulness, and pet talents beyond Unleashed Fury and Bestial Wrath.
 """
@@ -34,11 +38,14 @@ class HunterRotation:
     mode: str                 # "ranged" or "melee", whichever is higher
     mana_per_second: float    # of the chosen mode
     auto_dps: float = 0.0     # Auto Shot alone (costs no mana), the fallback once out of mana
+    aoe: tuple[str, ...] = ()  # abilities that hit more than one mob of the pack (#262)
+    parts: tuple[tuple[str, float], ...] = ()   # those abilities' DPS over the pack
 
 
 def hunter_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
-                    ranks: Mapping[int, int], target: Target, *, pet: bool = False) -> HunterRotation:
-    """Sustained DPS against `target`; `pet` adds a pet and turns Lone Wolf off."""
+                    ranks: Mapping[int, int], target: Target, *, pet: bool = False, pack: int = 1) -> HunterRotation:
+    """Sustained DPS against `target`; `pet` adds a pet and turns Lone Wolf off. With `pack` > 1, the
+    damage summed over a pack of that many such mobs (#262)."""
     c = load_toml(CONFIG)
     agi_per_crit = load_toml(MELEE)["hunter"]["agi_per_crit_at_60"]
     level = stats.level
@@ -70,6 +77,7 @@ def hunter_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassDa
 
     # ranged
     ranged = mana_r = auto = 0.0
+    parts: dict[str, float] = {}
     if stats.ranged is not None:
         rap = stats.ranged_attack_power + int_ap + 2 * extra_agi + (c["trueshot_aura_rap"] if taken("Trueshot Aura") else 0)
         a_r = Attacker(level, rap, stats.ranged_crit_pct + crit_all, hit)
@@ -95,7 +103,10 @@ def hunter_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassDa
             else:
                 ev = ranged_shot(norm + shot.weapon_bonus, a_r, target,
                                  damage_pct=weapon_pct + total("damage_pct", name), crit_damage_pct=cd_r)
-            shots += ev / cooldown
+            n = min(pack, c["multi_shot_targets"]) if name == "Multi-Shot" else 1
+            shots += ev * n / cooldown
+            if n > 1:
+                parts[name] = ev * n / cooldown
             casting += shot.cast_time / cooldown
             mana_r += shot.mana_cost * efficiency / cooldown
         sting = learned("Serpent Sting")
@@ -105,6 +116,14 @@ def hunter_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassDa
                    * land_chance(a_r, target, can_dodge=False) / sting.duration)
             mana_r += sting.mana_cost * (1 + total("mana_cost_pct", "@sting") / 100) / sting.duration
         ranged = auto * (1 - casting) + shots + dot
+        volley = learned("Volley") if pack > 1 else None
+        if volley is not None and volley.duration > 0:
+            # channelled back to back instead of shooting
+            channel = (volley.periodic_damage * (1 + (total("damage_pct", "Volley") + shared_pct) / 100)
+                       * land_chance(a_r, target, can_dodge=False) * pack / volley.duration)
+            if channel > ranged:
+                ranged, mana_r = channel, volley.mana_cost * efficiency / volley.duration
+                parts = {"Volley": channel}
 
     # petless dual-wield melee
     melee = mana_m = 0.0
@@ -150,5 +169,16 @@ def hunter_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassDa
 
     mode = "ranged" if ranged >= melee else "melee"
     best = max(ranged, melee)
+    if mode == "melee":
+        parts = {}
+    trap = learned("Explosive Trap") if pack > 1 else None
+    if trap is not None and trap.cooldown > 0 and trap.max_damage > 0:
+        # placed on cooldown in either mode; its fire hits every mob
+        parts["Explosive Trap"] = ((trap.min_damage + trap.max_damage) / 2 * (1 + shared_pct / 100)
+                                   * pack / trap.cooldown)
+        best += parts["Explosive Trap"]
+        trap_mana = trap.mana_cost / trap.cooldown
+        mana_r, mana_m = mana_r + trap_mana, mana_m + trap_mana
     return HunterRotation(dps=best + pet_dps, ranged_dps=ranged, melee_dps=melee, pet_dps=pet_dps, mode=mode,
-                          mana_per_second=mana_r if mode == "ranged" else mana_m, auto_dps=auto)
+                          mana_per_second=mana_r if mode == "ranged" else mana_m, auto_dps=auto,
+                          aoe=tuple(parts), parts=tuple(parts.items()))
diff --git a/src/wowforever/melee_scenarios.py b/src/wowforever/melee_scenarios.py
index fc15b42..9369e34 100644
--- a/src/wowforever/melee_scenarios.py
+++ b/src/wowforever/melee_scenarios.py
@@ -141,8 +141,8 @@ def rotation_output(class_name: str, stats: MeleeStats, spells: Sequence[SpellRa
     """The class rotation's DPS, mana use and out-of-mana fallback against `target`. For a hybrid,
     `melee` fixes the playstyle (a Feral leveling path is a cat even while its points sit in Balance);
     by default it follows the tree with most points. `pack` > 1 sums damage over that many mobs for
-    classes whose AoE abilities are modeled (warrior, rogue and Enhancement shaman, #262); the others stay
-    single target."""
+    classes whose AoE abilities are modeled (warrior, rogue, hunter and Enhancement shaman, #262); the
+    others stay single target."""
     from wowforever.classes import class_module
 
     module = class_module(class_name)
@@ -173,8 +173,8 @@ def rotation_output(class_name: str, stats: MeleeStats, spells: Sequence[SpellRa
     if class_name == "hunter":
         from wowforever.classes.hunter_rotation import hunter_rotation
 
-        r = hunter_rotation(stats, spells, cls, ranks, target, pet=_has_pet(cls, ranks))
-        return Output(r.dps, r.mana_per_second, r.auto_dps + r.pet_dps)
+        r = hunter_rotation(stats, spells, cls, ranks, target, pet=_has_pet(cls, ranks), pack=pack)
+        return Output(r.dps, r.mana_per_second, r.auto_dps + r.pet_dps, r.aoe)
     if class_name == "paladin":
         from wowforever.classes.paladin_rotation import paladin_rotation
 
```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_hunter_aoe.py` fails with `TypeError` (`pack` is not an argument of `hunter_rotation`). That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), one file at a time, with each file's hunks in file order.

## Done when
`.venv/Scripts/python -m pytest tests/test_hunter_aoe.py tests/test_hunter_rotation.py tests/test_aoe_score.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`. Do not run the slow tests.
