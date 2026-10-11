# Task #265 step 1: Thorns in the duel model

Make `tests/test_thorns_pvp.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `config/assumptions.toml`, `config/pvp_self.toml` and `src/wowforever/pvp/class_pvp.py`.

## Why
A druid's Thorns returns damage to every melee attacker. The client gives it no spell power coefficient, but that may be decided server-side, and the owner suspects Forever's spell power gear makes it scale. So the coefficient is an explicit assumption toggle, and the duel model counts Thorns as extra damage against melee opponents (the `MageSide.nova_dps` field, which `duel()` already adds only against melee kits).

## Change
1. **`config/assumptions.toml`:** append
   ```toml
   [thorns_spell_power_coefficient]
   value = 0.0
   options = [0.0, 0.168]
   why = "The client gives Thorns (damage shield, aura 15) no spell power coefficient, but damage-shield scaling can be server-side; Forever's spell power gear may make Thorns scale (owner question, #265)."
   source = "client SpellEffect 9910 EffectBonusCoefficient 0 (build 1.60.1.70338); 0.168 is a later expansion's value, used only as the alternative to test"
   tested = ""
   talents = []
   ```
2. **`config/pvp_self.toml`:** after the `own_armor = ...` line, add
   ```toml
   # melee hits a melee opponent lands per second (swings plus instant attacks): Thorns returns damage per hit (#265). Estimate.
   opponent_melee_hits_per_second = 1.0
   ```
3. **`src/wowforever/pvp/class_pvp.py`:**
   - Add the function:
     ```python
     def thorns_dps(thorns: SpellRank | None, spell_power: float, coefficient: float, hits_per_second: float) -> float:
         """Damage per second Thorns returns to a melee attacker (#265): (base + coefficient x spell power) per hit."""
         if thorns is None or thorns.damage_shield <= 0:
             return 0.0
         return (thorns.damage_shield + coefficient * spell_power) * hits_per_second
     ```
   - `class_side` gets a keyword parameter `assumptions: Assumptions | None = None` (import `Assumptions` from `wowforever.assumptions`; use `Assumptions.load()` when it's None). In it:
     ```python
     row = build_stats(class_name, stats, cls, ranks)
     thorns = thorns_dps(best_rank(spells, "Thorns", stats.level), getattr(row, "spell_power", 0.0),
                         assumptions["thorns_spell_power_coefficient"], raw.get("opponent_melee_hits_per_second", 0.0))
     ```
     Pass `nova_dps=thorns` to `MageSide(...)`, and use `row.health` for `health=` instead of calling `build_stats` a second time. Import `best_rank` from `wowforever.scenarios` and `SpellRank` from `wowforever.schema` (`ClassData` is already imported from there).
   - Add one line to the module docstring: Thorns returns damage to melee opponents (#265).

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_thorns_pvp.py` fails with `ImportError: cannot import name 'thorns_dps'`. That's the expected failure. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above.

## Done when
`.venv/Scripts/python -m pytest tests/test_thorns_pvp.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"` (about 10 seconds).
