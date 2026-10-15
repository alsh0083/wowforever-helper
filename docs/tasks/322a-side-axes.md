# Task #322, part A: survival, control and battleground from a duel side

Make `tests/test_side_axes.py`'s side tests pass. This is a refactor, so no score and no build description may change. Edit only these files, in this order:
1. `src/wowforever/pvp/duel.py`
2. `src/wowforever/calc/pvp_axes.py` (append at the end)
3. `src/wowforever/pvp/battleground.py` (append at the end)

Do not edit the tests.

## Why
Decision #315 (option 1): every class gets the battleground score, which needs the survival and control axes. Those axes and the battleground score were built from a mage `Character` and filler. They now read a duel `Side`, which every class engine builds (#318), so they work for every class. The mage's numbers must not change. Wiring them into reports is #323.

## The exact change
Apply this diff. It is the reference implementation, already checked against the tests and all regenerated reports. Write each file's hunks with `tools/apply_patch.py` (see AGENTS.md); `tools/local_agent.py` already sets `CODEX_EXE` for it. Hunk headers are a bare `@@` (no line counts). Don't re-verify context you can see in the diff; the hunks match the files on this branch. New blocks go at the end of their file.

```diff
diff --git a/src/wowforever/pvp/duel.py b/src/wowforever/pvp/duel.py
index e8af5d2..7179481 100644
--- a/src/wowforever/pvp/duel.py
+++ b/src/wowforever/pvp/duel.py
@@ -87,6 +87,10 @@ class Side:
     root_break_health: float = 0.0  # damage that breaks its root, share of the target's health; 0 = never (#286)
     root_duration: float = 0.0  # seconds one root lasts unbroken
     stun_aoe: float = 0.0  # the part of `stun` from controls that hit every nearby enemy (#287)
+    pushback: float = 0.0  # protection from spell pushback, 0-1 (#322)
+    escapes: float = 0.0  # escape cooldowns per minute (Blink, Frost Nova, Vanish, ...) (#322)
+    mana: float = 0.0  # mana pool; 0 for rage and energy classes (#322)
+    mana_per_second: float = 0.0  # mana drain while fighting (#322)
 
 
 @dataclass(frozen=True)
diff --git a/src/wowforever/calc/pvp_axes.py b/src/wowforever/calc/pvp_axes.py
index 26f5964..54ff950 100644
--- a/src/wowforever/calc/pvp_axes.py
+++ b/src/wowforever/calc/pvp_axes.py
@@ -145,3 +145,17 @@ def _score(axis: str, components: dict[str, float]) -> AxisScore:
     score = sum(s["weight"] * min(1.0, components[name] / s["reference"])
                 for name, s in spec.items())
     return AxisScore(score, components)
+
+
+def side_survival(side) -> AxisScore:
+    """The survival axis from a duel side (pvp.duel.Side), for any class (#322): absorbs per minute over
+    health, immunity, pushback protection and escapes. A mage side gives the same score as `survival`."""
+    return _score("survival", {"barrier": side.absorb_per_min / side.health if side.health else 0.0,
+                               "immunity": side.immunity_share, "pushback": side.pushback,
+                               "escapes": side.escapes})
+
+
+def side_control(side) -> AxisScore:
+    """The control axis from a duel side, for any class (#322); a mage side gives `control`'s score."""
+    return _score("control", {"slow": side.slow, "root": side.root, "stun": side.stun,
+                              "interrupt": side.interrupt})
diff --git a/src/wowforever/pvp/battleground.py b/src/wowforever/pvp/battleground.py
index 5a50cf6..826bf84 100644
--- a/src/wowforever/pvp/battleground.py
+++ b/src/wowforever/pvp/battleground.py
@@ -46,3 +46,29 @@ def best_battleground(char: Character, fillers, assumptions: Assumptions,
     if best is None:
         raise ValueError(f"no filler available at level {char.level}")
     return best
+
+
+def side_battleground(side, level: int, consensus: Consensus | None = None) -> dict:
+    """The battleground score of a duel side, any class (#322): kill from its DPS, endurance from its mana
+    pool and drain (rage and energy classes never run dry), survival and control from the side."""
+    from wowforever.calc.pvp_axes import side_control, side_survival
+
+    weights = (consensus or Consensus.load()).scenarios["battleground"].mid()
+    drain = side.mana_per_second
+    components = {"kill": min(1.0, side.dps / (KILL_REFERENCE * level / 60)),
+                  "endurance": 1.0 if drain <= 0 else min(1.0, side.mana / drain / ENDURANCE_SECONDS),
+                  "survival": side_survival(side).score, "control": side_control(side).score}
+    return {"score": sum(weights[k] * v for k, v in components.items()), "components": components}
+
+
+def best_side_battleground(sides, level: int, consensus: Consensus | None = None) -> dict:
+    """The battleground result of the side that scores best (ties: the earlier side), with its name
+    under "spell"."""
+    best: dict | None = None
+    for spell, side in sides:
+        result = side_battleground(side, level, consensus)
+        if best is None or result["score"] > best["score"]:
+            best = {**result, "spell": spell}
+    if best is None:
+        raise ValueError(f"no duel side at level {level}")
+    return best
```

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_side_axes.py` fails to import `side_control`. After this part, `test_a_mage_side_scores_like_the_mage_axes` and `test_other_classes_get_escapes_and_mana_on_their_side` still fail; part B fixes them. That is expected. Install nothing, make no network calls, and ask for no elevation. Iterate with `.venv/Scripts/python -m pytest tests/test_side_axes.py`, then run `.venv/Scripts/python -m pytest -m "not slow"` once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
In `tests/test_side_axes.py` the three tests that build a `Side` by hand pass; the only failures in `-m "not slow"` are the mage and other-classes tests in that file.
