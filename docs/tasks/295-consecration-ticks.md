# Task #295: Consecration's tick damage adds up both damage effects

Make `tests/test_consecration_ticks.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/normalize_spells.py`. The test docstring has the rule.

## Why
Forever's Consecration ticks through a tick spell with two damage effects that hit the same targets: 12 + 27 (coefficient 0.095) at rank 5. The importer reads only the first, so rank 5 comes out at 96 over 8 s instead of 312. On the cached 70291 tables, this change affects Consecration only.

## Change
Make exactly the changes in this diff (`-` lines go, `+` lines come, the rest is context). Turn it into a `tools/apply_patch.py` hunk with context copied from the file.

```diff
diff --git a/src/wowforever/normalize_spells.py b/src/wowforever/normalize_spells.py
index d7995cc..da1bbfb 100644
--- a/src/wowforever/normalize_spells.py
+++ b/src/wowforever/normalize_spells.py
@@ -192,10 +192,11 @@ def _by_spell(rows: list[dict[str, str]]) -> dict[int, dict[str, str]]:
 
 def _tick_damage_index(tables: Tables, sla_spells: set[int], names: dict[int, str],
                        levels: dict[int, dict[str, str]]) -> dict[tuple[str, int], tuple[float, float]]:
-    """(name, BaseLevel) -> (base points, coefficient) of a tick spell's damage effect.
+    """(name, BaseLevel) -> (base points, coefficient) of a tick spell's damage effects.
 
     A tick spell carries the tick damage of an area-triggered periodic: it shares the
-    parent spell's name and BaseLevel, has an Effect == 2 row, and is not trainable.
+    parent spell's name and BaseLevel, has an Effect == 2 row, and is not trainable. The lowest
+    such spell id wins; its Effect == 2 rows add up (Forever's Consecration ticks twice, #295).
     """
     best: dict[tuple[str, int], tuple[int, float, float]] = {}
     for row in tables["SpellEffect"]:
@@ -213,6 +214,8 @@ def _tick_damage_index(tables: Tables, sla_spells: set[int], names: dict[int, st
         current = best.get(key)
         if current is None or candidate[0] < current[0]:
             best[key] = candidate
+        elif candidate[0] == current[0]:
+            best[key] = (spell_id, current[1] + candidate[1], current[2] + candidate[2])
     return {key: (base_points, coefficient) for key, (_, base_points, coefficient) in best.items()}
 
 
```

Change nothing else. Leave the dataset files alone; Claude re-normalizes the data afterwards.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_consecration_ticks.py` fails with `AssertionError` (96 instead of 312). That's expected. Install nothing and ask for no elevation. Write the edit with `tools/apply_patch.py` (see AGENTS.md).

## Done when
`.venv/Scripts/python -m pytest tests/test_consecration_ticks.py tests/test_spell_siblings.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`.
