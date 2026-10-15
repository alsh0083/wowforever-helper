# Task #322, part B: every side fills pushback, escapes and mana

Make the whole suite pass. This is a refactor, so no score and no build description may change. Edit only these files, in this order:
1. `src/wowforever/classes/mage.py`
2. `src/wowforever/pvp/class_pvp.py`
3. `config/pvp_self.toml`

Do not edit the tests.

## Why
Decision #315 (option 1): every class gets the battleground score, which needs the survival and control axes. Those axes and the battleground score were built from a mage `Character` and filler. They now read a duel `Side`, which every class engine builds (#318), so they work for every class. The mage's numbers must not change. Wiring them into reports is #323.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/classes/mage.py b/src/wowforever/classes/mage.py
index 6912bc9..e991661 100644
--- a/src/wowforever/classes/mage.py
+++ b/src/wowforever/classes/mage.py
@@ -280,10 +280,10 @@ def duel_side(char, filler):
         if cooldown > 0:
             melee_bonus_dps = frozen_hit_gain(char, filler, target_level=char.level,
                                        assumptions=assumptions) / cooldown
+    rot = rotation(char, filler, target_level=char.level, assumptions=assumptions, sustained=False)
     return Side(
         health=health,
-        dps=rotation(char, filler, target_level=char.level,
-                     assumptions=assumptions, sustained=False).dps,
+        dps=rot.dps,
         absorb_per_min=s.components["barrier"] * health,
         immunity_share=s.components["immunity"],
         root=c.components["root"],
@@ -292,6 +292,10 @@ def duel_side(char, filler):
         interrupt=c.components["interrupt"],
         melee_bonus_dps=melee_bonus_dps,
         root_targets=2 if nova is not None else 1,   # Frost Nova roots every nearby enemy (#287)
+        pushback=s.components["pushback"],
+        escapes=s.components["escapes"],
+        mana=char.stats.mana,
+        mana_per_second=rot.mana_per_second,
     )
 
 
diff --git a/src/wowforever/pvp/class_pvp.py b/src/wowforever/pvp/class_pvp.py
index 6814e80..8af5e17 100644
--- a/src/wowforever/pvp/class_pvp.py
+++ b/src/wowforever/pvp/class_pvp.py
@@ -201,6 +201,10 @@ def class_side(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank],
                      sum(wide_locks.get(kind, 0.0) for kind in STOPS_ATTACKS)),
         root_break_health=assumptions["roots_break_health_pct"] / 100 * (1 + tougher / 100),
         root_duration=max(root_durations, default=0.0),
+        escapes=sum(60 / s.cooldown for name in cfg.get("escapes", ())
+                    if (s := best_rank(spells, name, stats.level)) is not None and s.cooldown > 0),
+        mana=getattr(row, "mana", 0.0),
+        mana_per_second=output.mana_per_second,
     )
 
 
diff --git a/config/pvp_self.toml b/config/pvp_self.toml
index e900abf..da840d7 100644
--- a/config/pvp_self.toml
+++ b/config/pvp_self.toml
@@ -11,6 +11,8 @@ own_armor = { rogue = 2500, hunter = 3500, warrior = 5000, paladin = 5000, pries
 opponent_melee_hits_per_second = 1.0
 
 [rogue]
+# escape cooldowns for the survival axis (#322); LOW confidence, Classic roles
+escapes = ["Sprint", "Vanish"]
 energy_per_minute = 600
 controls = [
   { name = "Kidney Shot", kind = "stun", duration = 6.0, cooldown = 20, energy = 125 },
@@ -20,6 +22,8 @@ controls = [
 ]
 
 [hunter]
+# escape cooldowns for the survival axis (#322); LOW confidence, Classic roles
+escapes = ["Feign Death"]
 energy_per_minute = 0
 controls = [
   { name = "Scatter Shot", kind = "disorient", duration = 4.0, cooldown = 30, requires = "Scatter Shot" },
@@ -31,6 +35,8 @@ slow_ranged = 0.167
 slow_melee = 0.6
 
 [warrior]
+# escape cooldowns for the survival axis (#322) (a fear to break away); LOW confidence, Classic roles
+escapes = ["Intimidating Shout"]
 # rage spent on controls, using the energy budget rules (estimate: half of ~10 rage/s at 60)
 energy_per_minute = 300
 controls = [
@@ -43,6 +49,8 @@ controls = [
 slow = 0.5
 
 [priest]
+# escape cooldowns for the survival axis (#322) (a fear to break away); LOW confidence, Classic roles
+escapes = ["Psychic Scream"]
 # casters spend mana, not a shared energy budget, on controls
 energy_per_minute = 0
 controls = [
@@ -54,6 +62,8 @@ controls = [
 slow = 0.17
 
 [warlock]
+# escape cooldowns for the survival axis (#322) (a fear to break away); LOW confidence, Classic roles
+escapes = ["Death Coil"]
 energy_per_minute = 0
 controls = [
   { name = "Fear", kind = "fear", duration = 4.0, cooldown = 15 },
@@ -76,6 +86,8 @@ hot_burst = "Swiftmend"
 heal_mana_share = 0.5
 
 [shaman]
+# escape cooldowns for the survival axis (#322) (snares pursuers); LOW confidence, Classic roles
+escapes = ["Earthbind Totem"]
 energy_per_minute = 0
 controls = [
   { name = "Earth Shock", kind = "interrupt", duration = 2.0, cooldown = 6 },
@@ -85,6 +97,8 @@ controls = [
 slow = 0.17
 
 [paladin]
+# escape cooldowns for the survival axis (#322) (frees itself from slows and roots); LOW confidence, Classic roles
+escapes = ["Blessing of Freedom"]
 energy_per_minute = 0
 controls = [
   { name = "Hammer of Justice", kind = "stun", duration = 6.0, cooldown = 60 },
```

## Environment note
The package is already installed in `.venv` (editable). Part A is done on this branch. Before you start, `test_a_mage_side_scores_like_the_mage_axes` and `test_other_classes_get_escapes_and_mana_on_their_side` fail. That is the expected failure. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_side_axes.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
