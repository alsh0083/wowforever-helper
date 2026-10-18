# Task #384 (Aftermath): a direct-only damage bonus

Make `tests/test_direct_damage_pct.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit in this order: `src/wowforever/schema.py`, `src/wowforever/calc/ev.py`,
  `src/wowforever/calc/talents.py`, `src/wowforever/classes/warlock.py`. Run the test file, then the fast suite once.
  Warlock regression pins (`tests/test_dungeon_mana.py`, opponent kits) may move; Claude re-derives them.
- Before you start, `tests/test_direct_damage_pct.py` fails.

## Why
Aftermath raises Immolate's initial damage only (10% per rank, 50% at 5/5), not its damage over time. The engine
has a single `damage_pct` for both, so it needs a direct-only bonus.

## Step 1: `src/wowforever/schema.py`
In `EFFECT_KINDS`, after the `"damage_pct",       # % more damage` line, add:
```python
    "direct_damage_pct",  # % more damage on the initial hit only, not the periodic part (Aftermath)
```

## Step 2: `src/wowforever/calc/ev.py`
1. In `class Modifiers`, after the `hit_bonus: float = 0.0` field, add:
```python
    direct_damage_pct: float = 0.0   # the initial hit only (Aftermath, #384)
```
2. In `expected_damage`, the line
```python
    avg = ((spell.min_damage + spell.max_damage) / 2.0 + spell.coefficient * spell_power) * damage_factor
```
   becomes
```python
    avg = (((spell.min_damage + spell.max_damage) / 2.0 + spell.coefficient * spell_power) * damage_factor
           * (1.0 + mods.direct_damage_pct / 100.0))
```

## Step 3: `src/wowforever/calc/talents.py`
In `_KIND_TO_FIELD`, after the `"hit_chance": "hit_bonus",` line, add:
```python
    "direct_damage_pct": "direct_damage_pct",
```

## Step 4: `src/wowforever/classes/warlock.py`
1. At the end of `TALENT_EFFECTS` (directly before its closing `}`), add:
```python
    "Aftermath": (
        EffectRule("direct_damage_pct", r"initial damage of your Immolate spell by (\d+(?:\.\d+)?)%", ("Immolate",)),
    ),
```
2. Delete the `UNMODELED` line `    "Aftermath": "control: Conflagrate dazes, stronger Immolate",`.

Nothing else changes.

## Done when
- `tests/test_direct_damage_pct.py` passes; no other new failures apart from warlock pins.
