# Task #263: AoE pulls in every class's report and PvE score

Make `tests/test_aoe_score.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `config/melee_scenarios.toml`, `src/wowforever/melee_scenarios.py`, `src/wowforever/report.py` and `dashboard/template.html`. The test docstring has the formulas.

## Why
#260 added `caster.aoe_pull`. This task puts AoE pulls into every non-mage class's report and PvE focus score. The score is seconds to clear a 3-mob pack, so lower is better. The dashboard's "★ best" badge also has to treat lower as better, including for the mage's existing AoE row (its break-even pack size).

## Change
1. **`config/melee_scenarios.toml`:** replace the `[references]` section with
   ```toml
   [aoe]
   # AoE pulls (#260, #263): seconds to clear a pack of this many same-level questing mobs
   pack = 3

   [references]
   # divisors that put the PvE parts on a common scale (as the mage's PVE_REFERENCES)
   questing = 100.0
   raid = 150.0
   dungeon = 150.0
   # AoE pulls count as aoe_seconds / seconds to clear the pack (the mage's aoe_seconds_3)
   aoe_seconds = 15.0
   ```
2. **`src/wowforever/melee_scenarios.py`:**
   - Just before `def pve_score(`, add
     ```python
     def aoe(class_name: str, stats: MeleeStats, spells, cls, ranks) -> tuple[float, str]:
         """Seconds to clear a pack of same-level questing mobs (#263) and the AoE spell used, or "single
         target". Spell-engine classes (and a hybrid's caster builds) mix their AoE spells into the rotation
         (caster.aoe_pull, #260); the others clear the pack with their single-target rotation until their AoE
         abilities are modeled (#262)."""
         from wowforever.classes import class_module

         module = class_module(class_name)
         pack = _config()["aoe"]["pack"]
         mob_hp = default_params("aoe", stats.level).mob_hp
         row = stats if getattr(module, "ENGINE", None) == "spell" else None
         if isinstance(stats, HybridStats):
             row = None if main_tree(cls, ranks) in module.MELEE_TREES else stats.caster
         if row is not None:
             from wowforever.caster import aoe_pull

             pull = aoe_pull(class_name, row, spells, cls, ranks, pack, mob_hp)
             return pull.seconds, pull.spell
         armor = _anchor_at(_config()["questing"]["anchors"], stats.level)[0]
         dps = rotation_output(class_name, stats, spells, cls, ranks, Target(0, armor)).dps
         return pack * mob_hp / dps, "single target"


     ```
   - In `pve_score`, replace the docstring with
     ```python
         """Mean of questing, raid, dungeon (with a weighted 5-player group, #220) and AoE pulls (#263), each
         divided by its reference (AoE: reference seconds / seconds to clear the pack)."""
     ```
     and replace its last line `            + group.typical_dungeon_dps(class_name, stats_at_max, cls, ranks) / ref["dungeon"]) / 3` with
     ```python
                 + group.typical_dungeon_dps(class_name, stats_at_max, cls, ranks) / ref["dungeon"]
                 + ref["aoe_seconds"] / aoe(class_name, stats_at_max, spells, cls, ranks)[0]) / 4
     ```
3. **`src/wowforever/report.py`:**
   - In `score_build` (the mage), change `"break_even": a.details["break_even"]}` to `"break_even": a.details["break_even"], "lower_better": True}`.
   - In `melee_report`, change `scores: dict[str, dict[int, dict[str, Any]]] = {"questing": {}, "dungeon": {}, "raid": {}}` to `scores: dict[str, dict[int, dict[str, Any]]] = {"questing": {}, "dungeon": {}, "raid": {}, "aoe": {}}`, and after the `scores["dungeon"][level] = {...}` statement (it ends with `"solo": round(ms.dungeon(class_name, stats, spells, cls, ranks), 1)}`) add
     ```python
                 seconds, spell = ms.aoe(class_name, stats, spells, cls, ranks)
                 scores["aoe"][level] = {"score": round(seconds, 1), "unit": "seconds (3-mob pack)", "spell": spell,
                                         "lower_better": True}
     ```
4. **`dashboard/template.html`, `function bestAt`:** replace the line
   ```
     if(best===null||row.score>best+1e-9){best=row.score;winners=[b]}
   ```
   with
   ```
     // lower_better rows (AoE pulls, #263): smaller wins; a 0 break-even pack means AoE never pays off
     if(row.lower_better&&row.score<=0)continue;
     if(best===null||(row.lower_better?row.score<best-1e-9:row.score>best+1e-9)){best=row.score;winners=[b]}
   ```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_aoe_score.py` fails with `AttributeError` (`melee_scenarios` has no `aoe`). That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above, with each file's hunks in file order. `dashboard/template.html` has very long lines; for step 4 use a hunk whose only context is the `if(!row)continue;` line just above.

## Done when
`.venv/Scripts/python -m pytest tests/test_aoe_score.py tests/test_caster_aoe.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`. Do not run the slow tests.
