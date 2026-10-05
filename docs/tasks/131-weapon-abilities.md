# Task #131 (part 1): weapon-damage abilities in the spell parser

Make `tests/test_weapon_abilities.py` pass without breaking the rest of the suite. Edit `src/wowforever/schema.py` and `src/wowforever/normalize_spells.py`. Do not edit the tests or fixtures.

## Why
Rogue abilities deal weapon damage, not spell damage. Sinister Strike is "normalized weapon damage + 68", Backstab is "(weapon damage + 150) × 150%", and Eviscerate adds damage per combo point. The parser only reads spell damage today, so these abilities come out with no damage.

## 1. `SpellRank` (schema.py): new last fields, all with defaults
```python
weapon_bonus: float = 0.0        # flat damage added to the weapon hit (effect 121 or 58 base points)
weapon_normalized: bool = False  # effect 121: normalized weapon damage (speed set by weapon type)
weapon_pct: float = 0.0          # effect 31 base points, e.g. 150 for 150%; 0 = no percentage effect
weapon_hits: int = 0             # weapon strikes per use: 1 for a direct effect, or the triggered count
per_combo_point: float = 0.0     # extra damage per combo point (EffectPointsPerResource of the damage effect)
combo_points: int = 0            # combo points awarded (effect 30 with EffectMiscValue_0 == 4)
haste_pct: float = 0.0           # melee haste aura (aura 319) base points
```

## 2. Parser (`_build_rank` in normalize_spells.py)
With `effects` the spell's own SpellEffect rows (base difficulty):
- **Direct weapon strike:** if an effect has `Effect` 121 or 58:
  - `weapon_bonus` = its `EffectBasePointsF`;
  - `weapon_normalized` = (Effect == 121);
  - `weapon_hits = 1`;
  - `weapon_pct` = the `EffectBasePointsF` of an effect with `Effect` 31, if any.
- **Triggered strikes:** otherwise, for each effect with `Effect` 64 whose `EffectTriggerSpell` has its own effect 121 or 58:
  - count it in `weapon_hits`;
  - take `weapon_bonus`, `weapon_normalized` and `weapon_pct` from the first such triggered spell, the same way.
  - Mutilate triggers two such spells, so it gets `weapon_hits = 2`.
- **Per combo point:** `per_combo_point` = `EffectPointsPerResource` of the `Effect` 2 (school damage) row, if any.
- **Combo points:** `combo_points` = `EffectBasePointsF` of an `Effect` 30 row whose `EffectMiscValue_0` is "4".
- **Haste:** `haste_pct` = `EffectBasePointsF` of an `Effect` 6 row whose `EffectAura` is "319".
- The triggered spells' rows live in the same SpellEffect table. Reach them through the same per-spell effect index the parser builds.

Existing fields don't change. Eviscerate keeps min/max 54–162 from base 108 with variance 1.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_weapon_abilities.py` fails with `AttributeError` on the new fields. That's the expected failure. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Start with `schema.py`, then `normalize_spells.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_weapon_abilities.py tests/test_spells.py tests/test_rogue.py`, then run the full suite once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
