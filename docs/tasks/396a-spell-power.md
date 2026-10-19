# Task #396/#398 (part 1): Demonic Knowledge, Mental Quickness, Improved Drains

Make `tests/test_spell_power_talents.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order; run the test file at the end, then the fast suite once. Warlock and
  shaman regression pins (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, opponent kits) may move;
  Claude re-derives them.
- Before you start, most tests in `tests/test_spell_power_talents.py` fail.

## Why
Demonic Knowledge gives spell power equal to a share of the level, Mental Quickness a share of Intellect, and
Improved Drains is a plain +20% on the drains. A new effect kind, `spell_power_from`, carries the first two:
`applies_to` names what the percentage is taken of (`"level"` or `"intellect"`).

## Step 1: `src/wowforever/caster.py`, `talent_stats`
1. Docstring: `"""The build's `stat_pct` talents (Mental Strength, Dark Inspiration; 70425, #356) through the
   class's conversions, then its `spell_power_from` talents (Demonic Knowledge, Mental Quickness, #396)."""`
2. Directly before the final `    return stats` add:
```python
    for talent in cls.talents:
        rank = ranks.get(talent.talent_id, 0)
        for effect in (talent.effects if rank > 0 else ()):
            if effect.kind == "spell_power_from":
                base = stats.level if effect.applies_to[0] == "level" else getattr(stats, effect.applies_to[0])
                stats = replace(stats, spell_power=stats.spell_power + base * effect.values[rank - 1] / 100)
```
   (`replace` is already imported from `dataclasses`.)

## Step 2: `src/wowforever/classes/warlock.py`
Add to `TALENT_EFFECTS`:
```python
    "Improved Drains": (
        EffectRule("damage_pct", r"Drain Life, Drain Soul, and Wrack spells by (\d+(?:\.\d+)?)%",
                   ("Drain Life", "Drain Soul", "Wrack")),
    ),
    # the model's warlock keeps a demon out (#396)
    "Demonic Knowledge": (
        EffectRule("spell_power_from", r"by up to (\d+(?:\.\d+)?)% of your level", ("level",)),
    ),
```
and delete the `UNMODELED` lines for `"Improved Drains"` and `"Demonic Knowledge"`.

## Step 3: `src/wowforever/classes/shaman.py`
Add to `TALENT_EFFECTS`:
```python
    "Mental Quickness": (
        EffectRule("spell_power_from", r"by up to (\d+(?:\.\d+)?)% of your Intellect", ("intellect",)),
    ),
```
and delete the `UNMODELED` line `    "Mental Quickness": "damage: spell power from Intellect",`.

## Step 4: `src/wowforever/classes/shaman_rotation.py`, `enhancement_rotation`
1. Directly after the line `    spell_crit = min(1.0, (stats.crit_pct + total("crit_chance", "all")) / 100)` add:
```python
    spell_power = stats.intellect * total("spell_power_from", "intellect") / 100   # Mental Quickness (#398)
```
2. The line
   `        avg = (shock.min_damage + shock.max_damage) / 2 * (1 + total("damage_pct", "Earth Shock") / 100)`
   becomes
```python
        avg = (((shock.min_damage + shock.max_damage) / 2 + shock.coefficient * spell_power)
               * (1 + total("damage_pct", "Earth Shock") / 100))
```
3. The line
   `        avg = (nova.min_damage + nova.max_damage) / 2 * (1 + total("damage_pct", "Fire Nova") / 100)`
   becomes
```python
        avg = (((nova.min_damage + nova.max_damage) / 2 + nova.coefficient * spell_power)
               * (1 + total("damage_pct", "Fire Nova") / 100))
```

Nothing else changes.

## Done when
- `tests/test_spell_power_talents.py` passes (7 tests); no other new failures apart from warlock and shaman pins.
