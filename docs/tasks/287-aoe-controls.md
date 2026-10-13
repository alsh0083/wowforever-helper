# Task #287 (controls part): multi-target controls reach both opponents when outnumbered

Make `tests/test_outnumbered_aoe_controls.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/pvp/duel.py` and `src/wowforever/pvp/class_pvp.py`. The test docstring has the hand-worked numbers.

## Why
In the 2v1 score the defender's stuns are split between the two opponents. Psychic Scream and Intimidating Shout fear up to 5 enemies (data MaxTargets 5), so they reach both opponents in full. Frost Nova roots every nearby enemy.

## Change
Make exactly the changes in this diff (`-` lines go, `+` lines come, the rest is context). Turn it into `tools/apply_patch.py` hunks: same files, same order, context copied from the files.

```diff
diff --git a/src/wowforever/pvp/class_pvp.py b/src/wowforever/pvp/class_pvp.py
index 03a12cd..ba82ad7 100644
--- a/src/wowforever/pvp/class_pvp.py
+++ b/src/wowforever/pvp/class_pvp.py
@@ -156,9 +156,14 @@ def class_side(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank],
     raw = load_toml(CONFIG)
     cfg = raw[class_name]
     taken = {t.name for t in cls.talents if ranks.get(t.talent_id, 0) > 0}
+    entries = [c for c in cfg["controls"] if c.get("requires") is None or c["requires"] in taken]
     controls = [Control(c["kind"], float(c["duration"]), float(c["cooldown"]), float(c.get("energy", 0.0)))
-                for c in cfg["controls"] if c.get("requires") is None or c["requires"] in taken]
+                for c in entries]
     locks = lockout_seconds(controls, cfg.get("energy_per_minute", 0.0))
+    # controls whose spell hits several enemies (data MaxTargets > 1: Psychic Scream, Intimidating Shout)
+    wide = [ctrl for ctrl, c in zip(controls, entries)
+            if (spell := best_rank(spells, c["name"], stats.level)) is not None and spell.max_targets > 1]
+    wide_locks = lockout_seconds(wide, cfg.get("energy_per_minute", 0.0))
     output = rotation_output(class_name, stats, spells, cls, ranks, Target(0, raw["player_armor"]))
     slow = cfg.get("slow", 0.0)
     if class_name == "hunter":
@@ -196,6 +201,8 @@ def class_side(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank],
         heal_hps=heal_hps,
         heal_budget=heal_budget,
         root_targets=1 + int(extra),
+        stun_aoe=min(sum(locks.get(kind, 0.0) for kind in STOPS_ATTACKS),
+                     sum(wide_locks.get(kind, 0.0) for kind in STOPS_ATTACKS)),
         root_break_health=assumptions["roots_break_health_pct"] / 100 * (1 + tougher / 100),
         root_duration=max(root_durations, default=0.0),
     )
diff --git a/src/wowforever/pvp/duel.py b/src/wowforever/pvp/duel.py
index abdecc3..6024081 100644
--- a/src/wowforever/pvp/duel.py
+++ b/src/wowforever/pvp/duel.py
@@ -90,6 +90,7 @@ class MageSide:
     root_targets: int = 1  # opponents its roots hold at once (Overgrowth, #278)
     root_break_health: float = 0.0  # damage that breaks its root, share of the target's health; 0 = never (#286)
     root_duration: float = 0.0  # seconds one root lasts unbroken
+    stun_aoe: float = 0.0  # the part of `stun` from controls that hit every nearby enemy (#287)
 
 
 @dataclass(frozen=True)
@@ -289,7 +290,8 @@ def outnumbered(side: MageSide, first: Kit, second: Kit) -> DuelResult:
     """The defender against two opponents at once, killing `first` then `second` (#278).
 
     Phase 1 (both alive): both kits' lockouts add up; the defender's stuns, slows and interrupts are
-    split between them by outnumbered_control_split; roots hold the opponent not being attacked, and
+    split between them by outnumbered_control_split, except stun_aoe (multi-target controls), which
+    reaches both; roots hold the opponent not being attacked, and
     the attacked one too with root_targets >= 2 until damage breaks them (#286). Phase 2: `second`
     alone, as in a duel. Healing happens in phase 1, with roots unbroken while it lasts (#290), and
     counts only if the score rises. mage_uptime and opponent_uptime are phase 1's, the latter for
@@ -316,8 +318,9 @@ def outnumbered(side: MageSide, first: Kit, second: Kit) -> DuelResult:
     t1, t2 = kill_time(first, u1), kill_time(second, u2)
 
     split = c["outnumbered_control_split"]
-    shared = dataclasses.replace(side, stun=side.stun * split, slow=side.slow * split,
-                                 interrupt=side.interrupt * split)
+    # multi-target controls (Psychic Scream, Frost Nova) reach both opponents; the rest is split (#287)
+    stun = (side.stun - side.stun_aoe) * split + side.stun_aoe
+    shared = dataclasses.replace(side, stun=stun, slow=side.slow * split, interrupt=side.interrupt * split)
     focus = dataclasses.replace(shared, root=side.root * root_hold(side, first) if side.root_targets >= 2 else 0.0)
     d_first, first_uptime = incoming(first, focus)
     net1 = d_first + incoming(second, shared)[0] - barrier([first, second])
@@ -398,4 +401,5 @@ def mage_side(char: Character, filler: SpellRank) -> MageSide:
         slow=c.components["slow"],
         interrupt=c.components["interrupt"],
         nova_dps=nova_dps,
+        root_targets=2 if nova is not None else 1,   # Frost Nova roots every nearby enemy (#287)
     )
```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_outnumbered_aoe_controls.py` fails (`stun_aoe` is not a field yet). That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), one file at a time, with each file's hunks in file order.

## Done when
`.venv/Scripts/python -m pytest tests/test_outnumbered_aoe_controls.py tests/test_outnumbered.py tests/test_class_pvp.py tests/test_duel.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`. Do not run the slow tests.
