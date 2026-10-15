# Task #321: per-class consensus talent tiers

Make `tests/test_consensus.py` and `tests/test_focus.py` pass without breaking the rest of the suite. Mage's scores must not change. Edit only these files, in this order:
1. `config/consensus.toml`
2. `src/wowforever/consensus.py`
3. `src/wowforever/focus.py`

Do not edit the tests.

## Why
Decision #315: every class gets the consensus PvP bonus. Talent tiers become per class (`[tiers.<class>.<scenario>]`). Mage's tiers move unchanged, and other classes get theirs from research (#320).

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and a regenerated mage report. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md). In `config/consensus.toml` only five section headers change, plus one comment line.

```diff
diff --git a/config/consensus.toml b/config/consensus.toml
index 966df47..e697ac9 100644
--- a/config/consensus.toml
+++ b/config/consensus.toml
@@ -111,28 +111,29 @@ note = "Group fights: AoE control and survival under focus; Forever AoE nerfs ma
 
 # ---- talent tiers per scenario (core > strong) ------------------------------------------------
 # Talents named here get a consensus bonus on top of modeled value in v1 scoring (#25/#28).
+# Per class: [tiers.<class>.<scenario>] (#321). A class without tiers gets no bonus.
 
-[tiers.wpvp_melee]
+[tiers.mage.wpvp_melee]
 core = ["Ice Barrier", "Ice Block", "Cold Snap", "Permafrost", "Improved Frost Nova"]
 strong = ["Frostbite", "Shatter", "Arctic Reach", "Improved Cone of Cold", "Blast Wave"]
 sources = ["barrens_pvp_builds", "wt_tbc_frost_pvp", "bnet_forever_mage_pvp"]
 
-[tiers.wpvp_caster]
+[tiers.mage.wpvp_caster]
 core = ["Ice Barrier", "Ice Block", "Cold Snap"]
 strong = ["Burning Soul", "Improved Counterspell", "Impact", "Shatter"]
 sources = ["bnet_forever_mage_pvp", "prior_research"]
 
-[tiers.stealth_ambush]
+[tiers.mage.stealth_ambush]
 core = ["Ice Barrier", "Ice Block", "Cold Snap", "Improved Frost Nova"]
 strong = ["Permafrost", "Frostbite", "Blast Wave", "Impact"]
 sources = ["bnet_forever_mage_pvp", "barrens_pvp_builds"]
 
-[tiers.battleground]
+[tiers.mage.battleground]
 core = ["Ice Block", "Cold Snap", "Ice Barrier"]
 strong = ["Improved Frost Nova", "Permafrost", "Blast Wave", "Improved Blizzard"]
 sources = ["barrens_pvp_builds"]
 
-[tiers.questing]
+[tiers.mage.questing]
 core = ["Improved Frostbolt", "Elemental Precision"]
 strong = ["Ice Shards", "Shatter", "Frostbite", "Permafrost"]
 sources = ["method_forever_leveling", "wt_forever_mage"]
diff --git a/src/wowforever/consensus.py b/src/wowforever/consensus.py
index 37222e8..9812d26 100644
--- a/src/wowforever/consensus.py
+++ b/src/wowforever/consensus.py
@@ -35,7 +35,7 @@ class ScenarioWeights:
 class Consensus:
     sources: dict[str, dict]
     scenarios: dict[str, ScenarioWeights]
-    tiers: dict[str, dict[str, tuple[str, ...]]]  # scenario -> {"core": (...), "strong": (...), "sources": (...)}
+    tiers: dict[str, dict[str, dict[str, tuple[str, ...]]]]  # class -> scenario -> {"core": (...), "sources": (...)}
     archetypes: dict = None  # shortlist thresholds and recognized hybrids (#28)
 
     @classmethod
@@ -46,11 +46,16 @@ class Consensus:
                                   s["confidence"], s.get("note", ""))
             for name, s in raw["scenario"].items()
         }
-        tiers = {name: {k: tuple(v) for k, v in t.items()} for name, t in raw.get("tiers", {}).items()}
+        tiers = {class_name: {name: {k: tuple(v) for k, v in t.items()} for name, t in by_scenario.items()}
+                 for class_name, by_scenario in raw.get("tiers", {}).items()}
         return cls(raw["sources"], scenarios, tiers, raw.get("archetypes", {}))
 
-    def problems(self, mage: ClassData | None = None) -> list[str]:
-        """Structural problems; with class data, also tier names that aren't talents."""
+    def tiers_for(self, class_name: str) -> dict[str, dict[str, tuple[str, ...]]]:
+        """The class's talent tiers by scenario (#321); empty for a class without any."""
+        return self.tiers.get(class_name, {})
+
+    def problems(self, cls: ClassData | None = None) -> list[str]:
+        """Structural problems; with a class's data, also its tier names that aren't its talents."""
         out = []
         for s in self.scenarios.values():
             total = sum(s.mid().values())
@@ -62,20 +67,21 @@ class Consensus:
             if s.confidence not in CONFIDENCE:
                 out.append(f"{s.name}: bad confidence {s.confidence!r}")
             out += [f"{s.name}: unknown source {src!r}" for src in s.sources if src not in self.sources]
-        for name, t in self.tiers.items():
-            out += [f"tiers.{name}: unknown source {src!r}" for src in t.get("sources", ())
-                    if src not in self.sources]
-            if mage is not None:
-                known = {x.name for x in mage.talents}
-                out += [f"tiers.{name}: {n!r} is not a talent" for tier in TIERS
-                        for n in t.get(tier, ()) if n not in known]
+        for class_name, by_scenario in self.tiers.items():
+            for name, t in by_scenario.items():
+                out += [f"tiers.{class_name}.{name}: unknown source {src!r}" for src in t.get("sources", ())
+                        if src not in self.sources]
+                if cls is not None and cls.class_name == class_name:
+                    known = {x.name for x in cls.talents}
+                    out += [f"tiers.{class_name}.{name}: {n!r} is not a talent" for tier in TIERS
+                            for n in t.get(tier, ()) if n not in known]
         return out
 
-    def tier_confidence(self, scenario: str, talent: str, mage: ClassData) -> str:
+    def tier_confidence(self, scenario: str, talent: str, cls: ClassData) -> str:
         """Confidence of one tier entry: low when all its sources predate Forever and Forever
         changed the talent; otherwise the scenario's confidence."""
-        eras = {self.sources[s]["era"] for s in self.tiers[scenario].get("sources", ())}
-        status = mage.talent_named(talent).classic_status
+        eras = {self.sources[s]["era"] for s in self.tiers_for(cls.class_name)[scenario].get("sources", ())}
+        status = cls.talent_named(talent).classic_status
         if eras and "forever" not in eras and status not in ("same", None):
             return "low"
         return self.scenarios[scenario].confidence if scenario in self.scenarios else "low"
diff --git a/src/wowforever/focus.py b/src/wowforever/focus.py
index 74ac9cc..d36501f 100644
--- a/src/wowforever/focus.py
+++ b/src/wowforever/focus.py
@@ -28,10 +28,11 @@ PVE_REFERENCES = {"questing": 100.0, "raid": 150.0, "aoe_seconds_3": 15.0, "dung
 ScoreFn = Callable[[Mapping[int, int]], float]
 
 
-def pvp_core_talents(consensus: Consensus) -> set[str]:
-    """Talent names the consensus tiers rate core in any world-PvP scenario."""
+def pvp_core_talents(consensus: Consensus, class_name: str = "mage") -> set[str]:
+    """Talent names the class's consensus tiers rate core in any world-PvP scenario."""
+    tiers = consensus.tiers_for(class_name)
     return {name for scenario in ("wpvp_melee", "wpvp_caster", "stealth_ambush")
-            for name in consensus.tiers.get(scenario, {}).get("core", ())}
+            for name in tiers.get(scenario, {}).get("core", ())}
 
 
 def pvp_score_fn(cls: ClassData, stats: Stats, assumptions: Assumptions, kits: list[Kit],
```

## Environment note
The package is already installed in `.venv` (editable). Before you start, the new tests fail: `AttributeError: 'Consensus' object has no attribute 'tiers_for'`, and `pvp_core_talents()` takes 1 positional argument. Those are the expected failures; implementing the diff is the task. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_consensus.py tests/test_focus.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest -m "not slow"` passes.
