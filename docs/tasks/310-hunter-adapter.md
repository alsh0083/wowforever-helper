# Task #310: hunter adapter; pet and range move into Output

Make `tests/test_class_engine.py` pass without breaking the rest of the suite. This is a refactor, so no score may change. Edit only these files, in this order:
1. `src/wowforever/classes/hunter.py` (append a block at the end)
2. `src/wowforever/melee_scenarios.py`
3. `src/wowforever/pvp/class_pvp.py`
4. `src/wowforever/describe.py`

Do not edit the tests.

## Why
The hunter becomes a `ClassEngine` like rogue, warrior and paladin (#309). Its pet and its range travel in `Output`, so questing and PvP stop asking whether the class is a hunter.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Don't re-verify context you can see in the diff; the hunks match the files on this branch.

```diff
diff --git a/src/wowforever/classes/hunter.py b/src/wowforever/classes/hunter.py
index 3286479..c66eb6e 100644
--- a/src/wowforever/classes/hunter.py
+++ b/src/wowforever/classes/hunter.py
@@ -126,3 +126,32 @@ ENGINE = "melee"
 
 # Hunter skill lines in SkillLineAbility: Beast Mastery, Marksmanship, Survival.
 SKILL_LINES = (50, 163, 51)
+
+
+# --- class engine (#310): this module is the hunter's ClassEngine ------------------------------------
+from wowforever.classes.engines import facts_later as facts  # noqa: E402
+
+
+def has_pet(cls, ranks) -> bool:
+    """A pet fights unless the build takes Lone Wolf."""
+    lone = next((t for t in cls.talents if t.name == "Lone Wolf"), None)
+    return lone is None or ranks.get(lone.talent_id, 0) <= 0
+
+
+def playstyle(cls, ranks) -> str:
+    return "ranged"
+
+
+def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None):
+    from wowforever.classes.hunter_rotation import hunter_rotation
+    from wowforever.melee_scenarios import Output
+
+    pet = has_pet(cls, ranks)
+    r = hunter_rotation(stats, spells, cls, ranks, target, pet=pet, pack=pack)
+    return Output(r.dps, r.mana_per_second, r.auto_dps + r.pet_dps, r.aoe, pet=pet, ranged=r.mode == "ranged")
+
+
+def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
+    from wowforever.classes.engines import pack_aoe
+
+    return pack_aoe(output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)
diff --git a/src/wowforever/describe.py b/src/wowforever/describe.py
index 0fec8f0..1f36892 100644
--- a/src/wowforever/describe.py
+++ b/src/wowforever/describe.py
@@ -230,9 +230,10 @@ def rotation_facts(class_name: str, cls: ClassData, ranks: Mapping[int, int], st
         return {"kind": "rogue", "builder": r.builder,
                 "split": {"auto-attacks": r.white_dps / r.dps, "abilities and poisons": r.yellow_dps / r.dps}}
     if class_name == "hunter":
+        from .classes.hunter import has_pet
         from .classes.hunter_rotation import hunter_rotation
 
-        pet = ms._has_pet(cls, ranks)
+        pet = has_pet(cls, ranks)
         r = hunter_rotation(stats, cls.spells, cls, ranks, target, pet=pet)
         split = {"pet": r.pet_dps / r.dps} if pet and r.dps else {}
         return {"kind": "hunter", "mode": r.mode, "pet": pet, "split": split}
diff --git a/src/wowforever/melee_scenarios.py b/src/wowforever/melee_scenarios.py
index 6799747..ccce7a6 100644
--- a/src/wowforever/melee_scenarios.py
+++ b/src/wowforever/melee_scenarios.py
@@ -72,11 +72,6 @@ def _config() -> dict:
     return load_toml(CONFIG)
 
 
-def _has_pet(cls: ClassData, ranks: Mapping[int, int]) -> bool:
-    lone = next((t for t in cls.talents if t.name == "Lone Wolf"), None)
-    return lone is None or ranks.get(lone.talent_id, 0) <= 0
-
-
 @dataclass(frozen=True)
 class HybridStats:
     """A caster class with melee builds (#175): its caster row and its melee row at one level.
@@ -166,15 +161,10 @@ def rotation_output(class_name: str, stats: MeleeStats, spells: Sequence[SpellRa
         gross = r.mana_per_second + r.regen_per_second
         # once dry, a caster keeps casting at the rate its regen pays for
         return Output(r.dps, r.mana_per_second, r.dps * min(1.0, r.regen_per_second / gross) if gross > 0 else r.dps)
-    if class_name in ("rogue", "warrior", "paladin"):
+    if class_name in ("rogue", "warrior", "paladin", "hunter"):
         from wowforever.classes import engine
 
         return engine(class_name).output(stats, spells, cls, ranks, target, pack=pack)
-    if class_name == "hunter":
-        from wowforever.classes.hunter_rotation import hunter_rotation
-
-        r = hunter_rotation(stats, spells, cls, ranks, target, pet=_has_pet(cls, ranks), pack=pack)
-        return Output(r.dps, r.mana_per_second, r.auto_dps + r.pet_dps, r.aoe)
     raise ValueError(f"no melee rotation for {class_name!r}")
 
 
@@ -186,10 +176,7 @@ def questing(class_name: str, stats: MeleeStats, spells, cls, ranks, *, melee: b
     out = rotation_output(class_name, stats, spells, cls, ranks, Target(0, armor),
                           drink_mana_per_second=q.drink_mana_per_second, melee=melee)
     kill = q.mob_hp / out.dps
-    if class_name != "hunter" or not _has_pet(cls, ranks):
-        downtime = mob_dps * kill / eat
-    else:
-        downtime = 0.0
+    downtime = 0.0 if out.pet else mob_dps * kill / eat     # a pet tanks while the hunter shoots
     if out.mana_per_second > 0:
         downtime = max(downtime, out.mana_per_second * kill / q.drink_mana_per_second)
     return 3600 / (kill + downtime + q.travel_seconds)
diff --git a/src/wowforever/pvp/class_pvp.py b/src/wowforever/pvp/class_pvp.py
index ba82ad7..ff522b8 100644
--- a/src/wowforever/pvp/class_pvp.py
+++ b/src/wowforever/pvp/class_pvp.py
@@ -166,13 +166,8 @@ def class_side(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank],
     wide_locks = lockout_seconds(wide, cfg.get("energy_per_minute", 0.0))
     output = rotation_output(class_name, stats, spells, cls, ranks, Target(0, raw["player_armor"]))
     slow = cfg.get("slow", 0.0)
-    if class_name == "hunter":
-        from wowforever.classes.hunter_rotation import hunter_rotation
-        from wowforever.melee_scenarios import _has_pet
-
-        mode = hunter_rotation(stats, spells, cls, ranks, Target(0, raw["player_armor"]),
-                               pet=_has_pet(cls, ranks)).mode
-        slow = cfg["slow_melee"] if mode == "melee" else cfg["slow_ranged"]
+    if "slow_ranged" in cfg:                    # a slow that depends on the range it fights at (hunter)
+        slow = cfg["slow_ranged"] if output.ranged else cfg["slow_melee"]
     row = build_stats(class_name, stats, cls, ranks)
     thorns = thorns_dps(best_rank(spells, "Thorns", stats.level), getattr(row, "spell_power", 0.0),
                         assumptions["thorns_spell_power_coefficient"], raw.get("opponent_melee_hits_per_second", 0.0))
```

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_class_engine.py` fails on `from wowforever.classes.hunter import has_pet` (ImportError). That's the expected failure. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_class_engine.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
