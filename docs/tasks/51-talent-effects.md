# Task #51: talent effects

Make `tests/test_talent_effects.py` pass. Do not edit the tests or fixtures.

## 1. `src/wowforever/classes/mage.py`: add two constants (keep `LAYOUT`)

- `TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]]`: one entry per **modeled** talent name.
- `UNMODELED: dict[str, str]`: every other mage talent name → a short reason (e.g. `"proc/stack mechanic, v1"`, `"utility: range"`, `"defensive spell, survival axis v1"`). Together the two dicts must cover **every** talent in the dataset exactly once.
- Put `EffectRule` in `src/wowforever/classes/__init__.py`: frozen dataclass `kind: str`, `pattern: str` (regex with **one** capture group for the number, matched against each rank's text), `applies_to: tuple[str, ...]`, `sign: int = 1` (use `-1` for reductions: cast time, mana cost).

`applies_to` tokens: school names (`"fire"`, `"frost"`, `"arcane"`), exact spell names (`"Fireball"`), `"all"`, and conditions starting with `@` (`"@frozen"`: only when the scenario says the target is frozen).

Model at least these (kind, applies_to); take the numbers from the text, never hard-code them:
| Talent | kind | applies_to |
|---|---|---|
| Ignite | dot_pct | fire |
| Critical Mass | crit_chance | fire |
| Fire Power | damage_pct | fire |
| Improved Fireball | cast_time (−) | Fireball, Frostfire Bolt |
| Incineration | crit_chance | Fire Blast, Ice Lance, Arcane Blast, Scorch |
| Improved Flamestrike | crit_chance | Flamestrike |
| Impact | proc_chance | fire |
| Burning Soul | pushback_pct | fire |
| Ice Shards | crit_damage_pct | frost |
| Piercing Ice | damage_pct | frost |
| Improved Frostbolt | cast_time (−) | Frostbolt |
| Improved Cone of Cold | damage_pct | Cone of Cold |
| Elemental Precision | hit_chance | fire, frost |
| Frost Channeling | mana_cost_pct (−) | frost |
| Shatter | crit_chance | all, @frozen |
| Arcane Instability | damage_pct **and** crit_chance | all |
| Arcane Impact | crit_chance | arcane |
| Arcane Focus | hit_chance | arcane |
| Arcane Mind | crit_damage_pct | arcane (the second number in its text) |

## 2. `src/wowforever/effects.py`

`attach_effects(cls: ClassData, rules, unmodeled) -> tuple[ClassData, list[str]]`: returns a copy of `cls` whose talents carry `Effect`s (`schema.Effect(kind, values, applies_to)`, one value per rank = `sign * float(match)`), plus a report of problems: a rule whose pattern doesn't match some rank's text (`"{talent}: rank {n} text didn't match {kind} pattern"`), and talent names in neither dict or in both. Talents in `UNMODELED` get no effects.

## 3. `src/wowforever/calc/talents.py`

`modifiers_for(spell: SpellRank, cls: ClassData, ranks: Mapping[int, int], conditions: Set[str] = frozenset()) -> Modifiers`: sum, over talents in `ranks` (talent id → rank), each effect's `values[rank - 1]` when the effect applies: `applies_to` has `"all"`, one of `spell.schools`, or `spell.name`, **and** every `@condition` token is in `conditions`. Mapping: damage_pct → `damage_pct`, crit_chance → `crit_chance_bonus`, crit_damage_pct → `crit_damage_bonus_pct`, dot_pct → `ignite_pct`, cast_time → `cast_time_delta`, mana_cost_pct → `mana_cost_pct`, hit_chance → `hit_bonus`. Other kinds don't affect `Modifiers`.

## 4. `src/wowforever/calc/ev.py`

Add `hit_bonus: float = 0.0` to `Modifiers` and use `hit_pct + mods.hit_bonus` for the miss chance in `expected_damage`. Existing tests must keep passing.

Standard library only, type hints, short docstrings.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
