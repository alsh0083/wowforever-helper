# Task #264: a gearing line in build descriptions

Make `tests/test_gearing_line.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/describe.py`.

## Why
Owner request: say more about gearing in each build's "About this build" text. Every build already carries `stat_weights` (per level `"20"`..`"60"`, or `{"generic": {...}}` for unscored builds), and the dashboard's Recommended gear panel ranks items with them. The new line tells the reader what those weights mean.

## Change
1. **Add to `src/wowforever/describe.py`, below `SCENARIO_LABELS`:**
   ```python
   # stats that appear on gear, in tie-break order; crit_pct/hit_pct and score are not gear stats
   GEAR_STATS = ("spell_power", "attack_power", "weapon_dps", "strength", "agility", "intellect", "spirit",
                 "stamina", "hit_rating", "crit_rating")
   GEAR_LABELS = {"spell_power": "spell power", "attack_power": "attack power", "weapon_dps": "weapon DPS",
                  "hit_rating": "hit rating", "crit_rating": "crit rating"}
   GEAR_PANEL = "The Recommended gear panel ranks items by these weights at your level."
   ```
2. **Add `gearing(weights: Mapping[str, Mapping[str, float]], levels: Sequence[int] = (30, 60), top: int = 4) -> str`** after `group_line`:
   - A helper `_priority(w)` returns the clause for one weight set: take the `GEAR_STATS` with weight > 0, sort by weight descending (ties keep `GEAR_STATS` order), keep the first `top`, and write each as `label ratio`. Here `label` is `GEAR_LABELS.get(stat, stat)`, and `ratio` is `f"{round(weight / best, 2):g}"`, with `best` the first stat's weight (so it prints `1`). Join the parts with `_join` (it already gives "a, b and c"). Return `""` when no stat qualifies.
   - When `"generic"` is in `weights`: return `"Gear priority per point (the class's default weights; this build has no scores): " + clause + ". " + GEAR_PANEL`, or `""` when the clause is empty.
   - Otherwise, for each level in `levels` whose `str(level)` is in `weights` and whose clause isn't empty, make `f"at level {level}, {clause}"`. With none, return `""`. Otherwise return `"Gear priority per point, relative to the best stat: " + "; ".join(parts) + ". " + GEAR_PANEL`.
3. **In `add_descriptions`**, just before `b["about"] = paragraphs`, add:
   ```python
   gear_line = gearing(b.get("stat_weights") or {})
   if gear_line:
       paragraphs.append(gear_line)
   ```
Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_gearing_line.py` fails with `ImportError: cannot import name 'gearing'`. That's the expected failure. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md).

## Done when
`.venv/Scripts/python -m pytest tests/test_gearing_line.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"` (about 10 seconds).
