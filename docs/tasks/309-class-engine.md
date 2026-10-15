# Task #309: ClassEngine interface; rogue, warrior and paladin adapters

Make `tests/test_class_engine.py` pass without breaking the rest of the suite. This is a refactor, so no score may change. Edit only these files, in this order:
1. `src/wowforever/classes/__init__.py`
2. `src/wowforever/classes/engines.py` (new)
3. `src/wowforever/classes/rogue.py`, `warrior.py`, `paladin.py`
4. `src/wowforever/melee_scenarios.py`

Do not edit the tests.

## Why
Five modules each choose a class's rotation with their own `if class_name ==` chain. From now on each scored class module runs its own rotation behind one interface, `ClassEngine` (docs/planning/2026-10-14-class-engine.md). This slice adds the interface and the three simplest adapters.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and the regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md). `engines.py` is a new file, so use `*** Add File:`. The three class modules get the same block appended at the end of the file, with the class name changed.

```diff
diff --git a/src/wowforever/classes/__init__.py b/src/wowforever/classes/__init__.py
index 7a54876..2f85dc2 100644
--- a/src/wowforever/classes/__init__.py
+++ b/src/wowforever/classes/__init__.py
@@ -3,9 +3,16 @@
 Everything outside this package is class-agnostic.
 """
 
-from collections.abc import Callable
+from __future__ import annotations
+
+from collections.abc import Callable, Mapping, Sequence
 from dataclasses import dataclass
-from typing import Match
+from typing import TYPE_CHECKING, Any, Match, Protocol
+
+if TYPE_CHECKING:
+    from wowforever.melee_scenarios import Output
+    from wowforever.physical import Target
+    from wowforever.schema import ClassData, SpellRank
 
 
 
@@ -66,3 +73,34 @@ def class_module(name: str):
     import importlib
 
     return importlib.import_module(CLASSES[name])
+
+
+class ClassEngine(Protocol):
+    """A scored class's rotation behind one interface (docs/planning/2026-10-14-class-engine.md).
+    The class module implements it with module-level functions; reach it through `engine(name)`."""
+
+    def playstyle(self, cls: ClassData, ranks: Mapping[int, int]) -> str:
+        """How the build fights: "melee", "ranged" or "caster"."""
+
+    def output(self, stats: Any, spells: Sequence[SpellRank], cls: ClassData, ranks: Mapping[int, int],
+               target: Target, *, pack: int = 1, drink_mana_per_second: float | None = None,
+               melee: bool | None = None) -> Output:
+        """The rotation's DPS, mana use and out-of-mana DPS against `target`, over `pack` mobs."""
+
+    def aoe(self, stats: Any, spells: Sequence[SpellRank], cls: ClassData, ranks: Mapping[int, int], *,
+            pack: int, mob_hp: float, armor: float) -> tuple[float, str]:
+        """Seconds to clear `pack` same-level mobs of `mob_hp`, and the AoE abilities used."""
+
+    def facts(self, stats: Any, cls: ClassData, ranks: Mapping[int, int]) -> dict[str, Any]:
+        """What the rotation does, for the build description."""
+
+
+ENGINE_MEMBERS = ("playstyle", "output", "aoe", "facts")
+
+
+def engine(name: str) -> ClassEngine:
+    """The class module registered under `name` as a ClassEngine; ValueError if it has none."""
+    module = class_module(name)
+    if not all(callable(getattr(module, member, None)) for member in ENGINE_MEMBERS):
+        raise ValueError(f"no class engine for {name!r}")
+    return module
diff --git a/src/wowforever/classes/engines.py b/src/wowforever/classes/engines.py
new file mode 100644
index 0000000..5b79888
--- /dev/null
+++ b/src/wowforever/classes/engines.py
@@ -0,0 +1,23 @@
+"""Shared ClassEngine pieces (docs/planning/2026-10-14-class-engine.md): class modules bind these
+instead of each writing its own."""
+
+from __future__ import annotations
+
+from collections.abc import Callable, Mapping, Sequence
+from typing import Any
+
+from wowforever.physical import Target
+from wowforever.schema import ClassData, SpellRank
+
+
+def pack_aoe(output: Callable[..., Any], stats: Any, spells: Sequence[SpellRank], cls: ClassData,
+             ranks: Mapping[int, int], *, pack: int, mob_hp: float, armor: float) -> tuple[float, str]:
+    """Seconds to clear the pack with the rotation run against it (`output(pack=...)`, #262), and its
+    AoE abilities, or "single target" where none hit several mobs."""
+    out = output(stats, spells, cls, ranks, Target(0, armor), pack=pack)
+    return pack * mob_hp / out.dps, ", ".join(out.aoe) or "single target"
+
+
+def facts_later(stats: Any, cls: ClassData, ranks: Mapping[int, int]) -> dict[str, Any]:
+    """Placeholder until the adapters gain their facts (#312)."""
+    raise NotImplementedError("rotation facts move behind the class engine in #312")
diff --git a/src/wowforever/classes/paladin.py b/src/wowforever/classes/paladin.py
index 1d40722..a4c1662 100644
--- a/src/wowforever/classes/paladin.py
+++ b/src/wowforever/classes/paladin.py
@@ -107,3 +107,25 @@ CAVEAT = ("Retribution model (#175): a two-hander's white swings with Seal of Co
           "Strike on cooldown; Holy damage ignores armor. Seal of Command's proc rate and Judgement of Command's "
           "damage are Classic values. Consecration, Exorcism, Hammer of Wrath, Vindication, Divine Strength and "
           "mana aren't modeled; base stats are estimates. Holy and Protection stay unscored.")
+
+
+# --- class engine (#309): this module is the paladin's ClassEngine ------------------------------------
+from wowforever.classes.engines import facts_later as facts  # noqa: E402
+
+
+def playstyle(cls, ranks) -> str:
+    return "melee"
+
+
+def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None):
+    from wowforever.classes.paladin_rotation import paladin_rotation
+    from wowforever.melee_scenarios import Output
+
+    r = paladin_rotation(stats, spells, cls, ranks, target, pack=pack)
+    return Output(r.dps, 0.0, r.dps, r.aoe)
+
+
+def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
+    from wowforever.classes.engines import pack_aoe
+
+    return pack_aoe(output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)
diff --git a/src/wowforever/classes/rogue.py b/src/wowforever/classes/rogue.py
index e0eb9ff..91db215 100644
--- a/src/wowforever/classes/rogue.py
+++ b/src/wowforever/classes/rogue.py
@@ -152,3 +152,25 @@ ENGINE = "melee"
 
 # Rogue skill lines in SkillLineAbility: Assassination, Combat, Subtlety, Poisons.
 SKILL_LINES = (253, 38, 39, 40)
+
+
+# --- class engine (#309): this module is the rogue's ClassEngine ------------------------------------
+from wowforever.classes.engines import facts_later as facts  # noqa: E402
+
+
+def playstyle(cls, ranks) -> str:
+    return "melee"
+
+
+def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None):
+    from wowforever.classes.rogue_rotation import rogue_rotation
+    from wowforever.melee_scenarios import Output
+
+    r = rogue_rotation(stats, spells, cls, ranks, target, pack=pack)
+    return Output(r.dps, 0.0, r.dps, r.aoe)
+
+
+def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
+    from wowforever.classes.engines import pack_aoe
+
+    return pack_aoe(output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)
diff --git a/src/wowforever/classes/warrior.py b/src/wowforever/classes/warrior.py
index 50824c4..37e0419 100644
--- a/src/wowforever/classes/warrior.py
+++ b/src/wowforever/classes/warrior.py
@@ -119,3 +119,25 @@ CAVEAT = ("Warrior model (#162): a two-hander's white swings build Rage for Mort
 # through wago.tools' documented file-info API (/api/info/{fdid}). Empty since build 1.60.1.70291: the four
 # it held (Improved Cleave, Precision, Toughness, Boundless Rage) left the trees (#239).
 ICON_OVERRIDES: dict[str, str] = {}
+
+
+# --- class engine (#309): this module is the warrior's ClassEngine ------------------------------------
+from wowforever.classes.engines import facts_later as facts  # noqa: E402
+
+
+def playstyle(cls, ranks) -> str:
+    return "melee"
+
+
+def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None):
+    from wowforever.classes.warrior_rotation import warrior_rotation
+    from wowforever.melee_scenarios import Output
+
+    r = warrior_rotation(stats, spells, cls, ranks, target, pack=pack)
+    return Output(r.dps, 0.0, r.dps, r.aoe)
+
+
+def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
+    from wowforever.classes.engines import pack_aoe
+
+    return pack_aoe(output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)
diff --git a/src/wowforever/melee_scenarios.py b/src/wowforever/melee_scenarios.py
index ab67c3c..6799747 100644
--- a/src/wowforever/melee_scenarios.py
+++ b/src/wowforever/melee_scenarios.py
@@ -64,6 +64,8 @@ class Output:
     mana_per_second: float
     fallback_dps: float   # DPS once out of mana (hunters: Auto Shot); equals dps for rogues
     aoe: tuple[str, ...] = ()   # abilities that hit several mobs of a pack (#262)
+    pet: bool = False           # a pet fights alongside (and tanks while questing)
+    ranged: bool = False        # the rotation fights from range
 
 
 def _config() -> dict:
@@ -164,26 +166,15 @@ def rotation_output(class_name: str, stats: MeleeStats, spells: Sequence[SpellRa
         gross = r.mana_per_second + r.regen_per_second
         # once dry, a caster keeps casting at the rate its regen pays for
         return Output(r.dps, r.mana_per_second, r.dps * min(1.0, r.regen_per_second / gross) if gross > 0 else r.dps)
-    if class_name == "rogue":
-        from wowforever.classes.rogue_rotation import rogue_rotation
+    if class_name in ("rogue", "warrior", "paladin"):
+        from wowforever.classes import engine
 
-        r = rogue_rotation(stats, spells, cls, ranks, target, pack=pack)
-        return Output(r.dps, 0.0, r.dps, r.aoe)
+        return engine(class_name).output(stats, spells, cls, ranks, target, pack=pack)
     if class_name == "hunter":
         from wowforever.classes.hunter_rotation import hunter_rotation
 
         r = hunter_rotation(stats, spells, cls, ranks, target, pet=_has_pet(cls, ranks), pack=pack)
         return Output(r.dps, r.mana_per_second, r.auto_dps + r.pet_dps, r.aoe)
-    if class_name == "paladin":
-        from wowforever.classes.paladin_rotation import paladin_rotation
-
-        r = paladin_rotation(stats, spells, cls, ranks, target, pack=pack)
-        return Output(r.dps, 0.0, r.dps, r.aoe)
-    if class_name == "warrior":
-        from wowforever.classes.warrior_rotation import warrior_rotation
-
-        r = warrior_rotation(stats, spells, cls, ranks, target, pack=pack)
-        return Output(r.dps, 0.0, r.dps, r.aoe)
     raise ValueError(f"no melee rotation for {class_name!r}")
 
 
```

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_class_engine.py` fails with `ImportError` on `ENGINE_MEMBERS` / `engine`. That's the expected failure; implementing the diff is the task. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_class_engine.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
