# Task #311, part A: caster adapters (priest, warlock) and the shared pieces

Make `tests/test_class_engine.py::test_casters_run_the_caster_rotation` pass. This is a refactor, so no score may change. Edit only these files, in this order:
1. `src/wowforever/classes/engines.py`
2. `src/wowforever/classes/priest.py`
3. `src/wowforever/classes/warlock.py`

Do not edit the tests.

## Why
The last four scored classes (priest, warlock, druid, shaman) become `ClassEngine`s, so `melee_scenarios.rotation_output` and `melee_scenarios.aoe` stop dispatching on the class. #311 runs in two parts on one branch; this is part A.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/classes/engines.py b/src/wowforever/classes/engines.py
index 5b79888..c713de6 100644
--- a/src/wowforever/classes/engines.py
+++ b/src/wowforever/classes/engines.py
@@ -18,6 +18,61 @@ def pack_aoe(output: Callable[..., Any], stats: Any, spells: Sequence[SpellRank]
     return pack * mob_hp / out.dps, ", ".join(out.aoe) or "single target"
 
 
+def caster_output(class_name: str, stats: Any, spells: Sequence[SpellRank], cls: ClassData,
+                  ranks: Mapping[int, int], target: Target, *, drink_mana_per_second: float | None = None) -> Any:
+    """The caster rotation's Output (caster.py, #163); once dry, a caster keeps casting at the rate its
+    regen pays for."""
+    from wowforever.caster import caster_rotation
+    from wowforever.melee_scenarios import Output
+
+    r = caster_rotation(class_name, stats, spells, cls, ranks, target, drink_mana_per_second=drink_mana_per_second)
+    gross = r.mana_per_second + r.regen_per_second
+    fallback = r.dps * min(1.0, r.regen_per_second / gross) if gross > 0 else r.dps
+    return Output(r.dps, r.mana_per_second, fallback, ranged=True)
+
+
+def caster_aoe(class_name: str, stats: Any, spells: Sequence[SpellRank], cls: ClassData,
+               ranks: Mapping[int, int], *, pack: int, mob_hp: float) -> tuple[float, str]:
+    """A caster's AoE spells mixed into its rotation (caster.aoe_pull, #260)."""
+    from wowforever.caster import aoe_pull
+
+    pull = aoe_pull(class_name, stats, spells, cls, ranks, pack, mob_hp)
+    return pull.seconds, pull.spell
+
+
+def melee_build(melee_trees: Sequence[str], cls: ClassData, ranks: Mapping[int, int]) -> bool:
+    """A hybrid's build fights in melee when most of its points sit in a melee tree (#175)."""
+    from wowforever.melee_scenarios import main_tree
+
+    return main_tree(cls, ranks) in melee_trees
+
+
+def hybrid_output(class_name: str, melee_trees: Sequence[str], melee_output: Callable[..., Any], stats: Any,
+                  spells: Sequence[SpellRank], cls: ClassData, ranks: Mapping[int, int], target: Target, *,
+                  pack: int = 1, drink_mana_per_second: float | None = None, melee: bool | None = None) -> Any:
+    """A hybrid's Output: its melee rotation on the melee stat row for a melee build (or `melee=True`, a
+    Feral leveling path while its points sit in Balance), else the caster rotation on the caster row."""
+    from wowforever.melee_scenarios import HybridStats
+
+    if isinstance(stats, HybridStats):
+        if melee if melee is not None else melee_build(melee_trees, cls, ranks):
+            return melee_output(stats.melee, spells, cls, ranks, target, pack=pack)
+        stats = stats.caster
+    return caster_output(class_name, stats, spells, cls, ranks, target, drink_mana_per_second=drink_mana_per_second)
+
+
+def hybrid_aoe(class_name: str, melee_trees: Sequence[str], output: Callable[..., Any], stats: Any,
+               spells: Sequence[SpellRank], cls: ClassData, ranks: Mapping[int, int], *,
+               pack: int, mob_hp: float, armor: float) -> tuple[float, str]:
+    """A melee build runs its rotation against the pack; a caster build mixes in its AoE spells."""
+    from wowforever.melee_scenarios import HybridStats
+
+    if isinstance(stats, HybridStats) and melee_build(melee_trees, cls, ranks):
+        return pack_aoe(output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)
+    row = stats.caster if isinstance(stats, HybridStats) else stats
+    return caster_aoe(class_name, row, spells, cls, ranks, pack=pack, mob_hp=mob_hp)
+
+
 def facts_later(stats: Any, cls: ClassData, ranks: Mapping[int, int]) -> dict[str, Any]:
     """Placeholder until the adapters gain their facts (#312)."""
     raise NotImplementedError("rotation facts move behind the class engine in #312")
diff --git a/src/wowforever/classes/priest.py b/src/wowforever/classes/priest.py
index 5b508e1..1c24db0 100644
--- a/src/wowforever/classes/priest.py
+++ b/src/wowforever/classes/priest.py
@@ -132,3 +132,23 @@ CAVEAT = ("Caster model (#163): Shadow Word: Pain and Devouring Plague kept up,
           "Death on cooldown, Mind Flay or Smite in between, with Classic hit, crit and mana rules. Shadow "
           "Weaving counts at full stacks; Vampiric Embrace's healing, Twin Disciplines and Improved Shadow "
           "Word: Pain's longer duration aren't modeled. Base stats are estimates; healer builds stay unscored.")
+
+
+# --- class engine (#311): this module is the priest's ClassEngine ------------------------------------
+from wowforever.classes.engines import facts_later as facts  # noqa: E402
+
+
+def playstyle(cls, ranks) -> str:
+    return "caster"
+
+
+def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None):
+    from wowforever.classes.engines import caster_output
+
+    return caster_output("priest", stats, spells, cls, ranks, target, drink_mana_per_second=drink_mana_per_second)
+
+
+def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
+    from wowforever.classes.engines import caster_aoe
+
+    return caster_aoe("priest", stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp)
diff --git a/src/wowforever/classes/warlock.py b/src/wowforever/classes/warlock.py
index 93341dc..85e9df2 100644
--- a/src/wowforever/classes/warlock.py
+++ b/src/wowforever/classes/warlock.py
@@ -130,3 +130,23 @@ CAVEAT = ("Caster model (#163, #165): Corruption, Bane of Agony and Immolate kep
           "then the best of Shadow Bolt, Incinerate, Searing Pain or Wrack, with Life Tap as steady mana. Pets, "
           "Siphon Life and Drain Life (health drains), Shadowburn, Nightfall and Improved Shadow Bolt procs aren't "
           "modeled; Demonic Sacrifice counts the Imp (+Shadow). Base stats are estimates.")
+
+
+# --- class engine (#311): this module is the warlock's ClassEngine ------------------------------------
+from wowforever.classes.engines import facts_later as facts  # noqa: E402
+
+
+def playstyle(cls, ranks) -> str:
+    return "caster"
+
+
+def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None):
+    from wowforever.classes.engines import caster_output
+
+    return caster_output("warlock", stats, spells, cls, ranks, target, drink_mana_per_second=drink_mana_per_second)
+
+
+def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
+    from wowforever.classes.engines import caster_aoe
+
+    return caster_aoe("warlock", stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp)
```

## Environment note
The package is already installed in `.venv` (editable). Before you start, `test_casters_run_the_caster_rotation` fails with `ValueError: no class engine for 'priest'`. That's the expected failure. Other tests in `tests/test_class_engine.py` (the hybrid and dispatch tests) still fail after this part; part B fixes them. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_class_engine.py -k casters`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest tests/test_class_engine.py -k casters` passes, and `-m "not slow"` fails only in `tests/test_class_engine.py`'s hybrid, every-class and dispatch tests.
