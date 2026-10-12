# Task #276: druid healing talents in self-healing

Make `tests/test_heal_talents.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/schema.py`, `src/wowforever/classes/druid.py` and `src/wowforever/pvp/class_pvp.py`. The test docstring has the hand-worked numbers.

## Why
`heal_capacity()` (#265) ignores talents, so Restoration heals exactly as much as Balance. Naturalist shortens Healing Touch, Gift of Nature adds healing, Tranquil Spirit cheapens Healing Touch. Moonglow cuts only *damaging* spells' mana cost, so heals must not pick up school-wide effects.

## Change
1. **`src/wowforever/schema.py`, `EFFECT_KINDS`:** after the `"mana_cost_pct",` line add
   ```python
       "healing_pct",      # % more healing (Gift of Nature)
   ```
2. **`src/wowforever/classes/druid.py`:**
   - In `TALENT_EFFECTS`, replace the `"Naturalist"` entry with
     ```python
         "Naturalist": (
             EffectRule("cast_time", r"cast time of your Healing Touch spell by (\d+(?:\.\d+)?) sec", ("Healing Touch",), sign=-1),
             EffectRule("damage_pct", r"increases all damage you deal by (\d+(?:\.\d+)?)%", ("all",)),
         ),
     ```
   - After the `"Reflection"` entry, add
     ```python
         # self-healing (#276)
         "Gift of Nature": (
             EffectRule("healing_pct", r"effect of all your healing spells by (\d+(?:\.\d+)?)%", ("all",)),
         ),
         "Tranquil Spirit": (
             EffectRule("mana_cost_pct", r"mana cost of your Healing Touch and Tranquility spells by (\d+(?:\.\d+)?)%",
                        ("Healing Touch", "Tranquility"), sign=-1),
         ),
     ```
   - In `UNMODELED`, delete the `"Gift of Nature": ...` and `"Tranquil Spirit": ...` lines.
3. **`src/wowforever/pvp/class_pvp.py`:**
   - Add above `heal_capacity`:
     ```python
     def heal_modifiers(spell: SpellRank, cls: ClassData, ranks: Mapping[int, int]) -> tuple[float, float, float]:
         """(cast time change in s, mana cost %, healing %) from taken talents for one heal (#276).

         Cast time and mana cost come only from effects naming the heal (Moonglow's school-wide cut is for
         damaging spells); healing % from every `healing_pct` effect."""
         cast = cost = healing = 0.0
         for talent_id, rank in ranks.items():
             if rank <= 0:
                 continue
             for effect in cls.talent(talent_id).effects:
                 value = effect.values[rank - 1]
                 if effect.kind == "healing_pct":
                     healing += value
                 elif spell.name in effect.applies_to and effect.kind == "cast_time":
                     cast += value
                 elif spell.name in effect.applies_to and effect.kind == "mana_cost_pct":
                     cost += value
         return cast, cost, healing
     ```
   - In `heal_capacity`, after the `continue` of the skip check, replace the `amount = ...` and `seconds = ...` lines with
     ```python
             cast, cost, healing = heal_modifiers(spell, cls, ranks)
             amount = ((spell.heal_min + spell.heal_max) / 2 + spell.heal_coefficient * sp) * (1 + healing / 100)
             seconds = max(GCD_SECONDS, spell.cast_time + cast)
             mana = spell.mana_cost * (1 + cost / 100)
     ```
     store `mana` in `best` instead of the spell (`best: tuple[float, float, float] | None`, `best = (amount, seconds, mana)`), and return `(amount / seconds, row.mana * cfg["heal_mana_share"] * amount / mana)`.
   - In `heal_capacity`'s docstring, after "per cast of max(GCD, cast time) seconds;" insert "talents change cast time, mana cost and healing (heal_modifiers, #276);".

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, four tests in `tests/test_heal_talents.py` fail with `AssertionError` and `test_feral_takes_no_healing_talents` passes. That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above. Patch hunks: anchor on non-blank lines (#275).

## Done when
`.venv/Scripts/python -m pytest tests/test_heal_talents.py tests/test_self_heal.py tests/test_class_pvp.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`.
