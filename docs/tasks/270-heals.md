# Task #270: direct and periodic heals in the spell import

Make `tests/test_spell_heals.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/schema.py` and `src/wowforever/normalize_spells.py`.

## Why
The importer reads no healing. Druid self-healing in duels (#265) needs heal amounts and coefficients from the client rows, read the same way damage is.

## Change
1. **`src/wowforever/schema.py`, `SpellRank`:** add after `damage_shield_coefficient`:
   ```python
   heal_min: float = 0.0                  # direct heal (Effect 10), with variance like damage (#270)
   heal_max: float = 0.0
   heal_coefficient: float = 0.0
   periodic_heal: float = 0.0             # heal over time (aura 8), total over the duration
   periodic_heal_coefficient: float = 0.0  # its spell power coefficient, total over the duration
   ```
2. **`src/wowforever/normalize_spells.py`:**
   - Constants, next to the others: `EFFECT_AREA_AURA = 35  # apply area aura (Tranquility)` and `AURA_PERIODIC_HEAL = 8  # heal over time`. `EFFECT_HEAL = 10` already exists.
   - In `_build_rank`, after the damage-shield lines:
     ```python
     heal = next((e for e in effects if e["Effect"] == str(EFFECT_HEAL)), None)
     heal_min = heal_max = heal_coefficient = 0.0
     if heal is not None:
         base, variance = _f(heal["EffectBasePointsF"]), _f(heal["Variance"])
         heal_min, heal_max = base * (1 - variance / 2), base * (1 + variance / 2)
         heal_coefficient = _f(heal["EffectBonusCoefficient"])
     hot = next((e for e in effects if e["Effect"] in (str(EFFECT_AURA), str(EFFECT_AREA_AURA))
                 and e["EffectAura"] == str(AURA_PERIODIC_HEAL)), None)
     periodic_heal = periodic_heal_coefficient = 0.0
     if hot is not None:
         ticks = _ticks(duration, _f(hot["EffectAuraPeriod"]) / 1000.0)
         periodic_heal = _f(hot["EffectBasePointsF"]) * ticks
         periodic_heal_coefficient = _f(hot["EffectBonusCoefficient"]) * ticks
     ```
     Pass the five values to `SpellRank(...)` by keyword.
Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, every test in `tests/test_spell_heals.py` fails with `AttributeError: 'SpellRank' object has no attribute 'heal_min'` (or `periodic_heal`). That's the expected failure. The test file imports helpers from `tests/test_spell_siblings.py`; leave both test files alone. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md): `schema.py` first, then `normalize_spells.py`.

## Done when
`.venv/Scripts/python -m pytest tests/test_spell_heals.py tests/test_spell_siblings.py tests/test_spells.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"` (about 10 seconds).
