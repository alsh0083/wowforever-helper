# Task #17: expected-value calculator core

Implement `src/wowforever/calc/ev.py` (+ `src/wowforever/calc/__init__.py`) so that `tests/test_ev_golden.py` passes. Do not edit the golden tests; if one looks wrong, stop and say why.

## Interface (exact names; the tests import them)

- `Modifiers` (frozen dataclass, all default 0): `damage_pct`, `crit_chance_bonus`, `crit_damage_bonus_pct`, `ignite_pct`, `cast_time_delta`, `mana_cost_pct`
- `miss_chance(caster_level: int, target_level: int, hit_pct: float) -> float`: percent, rules in the test module docstring
- `expected_damage(spell: SpellRank, *, spell_power, crit_pct, hit_pct, caster_level, target_level, mods: Modifiers, periodic_can_crit: bool = False) -> float`: direct + periodic + Ignite (fire-school spells only)
- `effective_cast_time(spell: SpellRank, mods: Modifiers) -> float`: cast time + delta, floored at the 1.5 s global cooldown
- `casts_to_oom(spell: SpellRank, mana: float, mods: Modifiers) -> int`: floor(mana / (cost * (1 + mana_cost_pct/100)))

`SpellRank` is in `wowforever.schema`. Pure functions, standard library only, type hints, short docstrings. Crit chance is capped at 100%.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
