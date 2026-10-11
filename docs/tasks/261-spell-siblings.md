# Task #261: Holy Nova and Fire Nova damage, Thorns damage shield

Make `tests/test_spell_siblings.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/schema.py` (two new fields) and `src/wowforever/normalize_spells.py`.

## Why
Three spells carry no damage in the normalized dataset (#261 has the client rows):
1. Holy Nova: each level has a damage spell (Effect 2) and a heal spell (Effect 10). Both are trainable, with the same name and BaseLevel, so both become ranks and the top "rank" is a heal.
2. Fire Nova: the trainable spell is Effect 3 (dummy); the damage is in non-trainable same-name spells at the same BaseLevel.
3. Thorns: a damage shield (aura 15) that no SpellRank field holds.

## Change
1. **`src/wowforever/schema.py`, `SpellRank`:** add after `combo_points`:
   ```python
   damage_shield: float = 0.0             # damage per melee hit taken (aura 15: Thorns), base points
   damage_shield_coefficient: float = 0.0  # spell power coefficient of that damage
   ```
2. **`normalize_spells.py`, `class_spells`, after `trainable.sort()`:** keep one spell per `(name, level)`:
   ```python
   trainable = _one_per_level(trainable, indexes) ...
   ```
   Move `indexes = _index_tables(tables)` above this so `_one_per_level` can use it. `_one_per_level(trainable, indexes)` walks the sorted `(name, level, spell_id)` list, groups entries with the same `(name, level)`, and keeps one per group: the first whose `indexes.effects.get(spell_id, [])` has an `Effect == "2"` row, else the first (the lowest id, since the list is sorted). Return the kept entries in their original order.
3. **Sibling damage:** add `_sibling_damage_index(tables, sla_spells, names, levels) -> dict[tuple[str, int], list[tuple[int, float, float, float]]]`, built like `_tick_damage_index`: for each base-difficulty SpellEffect row with `Effect == "2"` whose spell is NOT in `sla_spells` and has a name and a SpellLevels row, append `(spell_id, base points, Variance, coefficient)` under `(name, BaseLevel)`. Pass it to `_build_rank` as a new keyword `sibling_damage`. In `_build_rank`, after the periodic block, if `min_damage == 0` and `periodic_damage == 0` and `weapon_hits == 0` and `(name, level)` has siblings, take the sibling whose id is closest to `spell_id` (`min(..., key=lambda s: abs(s[0] - spell_id))`) and set `min_damage = base * (1 - variance / 2)`, `max_damage = base * (1 + variance / 2)` and `coefficient`.
4. **Damage shield:** in `_build_rank`, find the effect with `Effect == str(EFFECT_AURA)` and `EffectAura == "15"`. Add a constant `AURA_DAMAGE_SHIELD = 15` next to the other aura constants and use it. If found, set `damage_shield = _f(EffectBasePointsF)` and `damage_shield_coefficient = _f(EffectBonusCoefficient)`, and pass both to `SpellRank(...)`.

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, three tests in `tests/test_spell_siblings.py` fail (four Holy Nova ranks instead of two, Fire Nova 0 damage, no `damage_shield` field). That's the expected failure. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md): `schema.py` first, then `normalize_spells.py`.

## Done when
`.venv/Scripts/python -m pytest tests/test_spell_siblings.py tests/test_spells.py tests/test_spell_control.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"` (about 10 seconds).
