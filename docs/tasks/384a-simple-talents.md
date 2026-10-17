# Task #384 (part 1): Twin Disciplines, Reverberation, Shamanistic Focus, Elemental Focus, Fel Vitality

Make `tests/test_simple_talents.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order; run the test file at the end, then the fast suite once. Priest, shaman
  and warlock regression pins (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, opponent kits) may move;
  Claude re-derives them.
- Before you start, most tests in `tests/test_simple_talents.py` fail.

## Why
Each talent is a plain number in its rank text that an existing effect kind carries. Each one sits in `UNMODELED`.

## Step 1: `src/wowforever/stat_weights.py`, `_caster_apply`
Directly before the line `    if stat == "spell_power":` add:
```python
    if stat == "mana":                            # Fel Vitality's maximum mana (#384)
        return replace(stats, mana=stats.mana + amount)
```

## Step 2: `src/wowforever/classes/priest.py`
Add to `TALENT_EFFECTS` (anywhere inside the dict):
```python
    "Twin Disciplines": (
        EffectRule("damage_pct", r"instant cast spells by (\d+(?:\.\d+)?)%",
                   ("Shadow Word: Pain", "Devouring Plague", "Shadow Word: Death", "Holy Nova", "Chastise")),
    ),
```
and delete the `UNMODELED` line `    "Twin Disciplines": "damage: +5% instant spell damage and healing",`.

## Step 3: `src/wowforever/classes/shaman.py`
Add to `TALENT_EFFECTS`:
```python
    "Reverberation": (
        EffectRule("cooldown", r"cooldown of your Shock spells by (\d+(?:\.\d+)?) sec",
                   ("Earth Shock", "Flame Shock", "Frost Shock"), sign=-1),
    ),
    "Shamanistic Focus": (
        EffectRule("mana_cost_pct", r"Shock and Lightning Shield spells by (\d+(?:\.\d+)?)%",
                   ("Earth Shock", "Flame Shock", "Frost Shock", "Lightning Shield"), sign=-1),
    ),
    # best effort (#384): a 10% chance of a free next damage spell averages to 10% less mana
    "Elemental Focus": (
        EffectRule("mana_cost_pct", r"(\d+(?:\.\d+)?)% chance to enter a Clearcasting state",
                   ("fire", "frost", "nature"), sign=-1),
    ),
```
and delete the three `UNMODELED` lines for `"Reverberation"`, `"Elemental Focus"` and `"Shamanistic Focus"`.

## Step 4: `src/wowforever/classes/warlock.py`
Add to `TALENT_EFFECTS`:
```python
    "Fel Vitality": (
        EffectRule("stat_pct", r"increases your maximum Mana by (\d+(?:\.\d+)?)%", ("mana",)),
    ),
```
and delete the `UNMODELED` line `    "Fel Vitality": "pet: pet health and mana",`.

Nothing else changes.

## Done when
- `tests/test_simple_talents.py` passes (8 tests); no other new failures apart from priest, shaman and warlock pins.
