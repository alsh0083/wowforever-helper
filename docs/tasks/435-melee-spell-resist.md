# Task #435: level resistance for spell damage inside the melee engines

Make `tests/test_melee_spell_resist.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit in this order: `src/wowforever/calc/ev.py`, `src/wowforever/classes/shaman_rotation.py`,
  `src/wowforever/classes/rogue_rotation.py`, `src/wowforever/classes/hunter_rotation.py`. Run the test file, then
  the fast suite once and report other failures (shaman, rogue and hunter score pins may move; Claude re-pins).
- Before you start, `tests/test_melee_spell_resist.py` fails to import.

## Why
#409 made spells against higher-level targets lose the average level resist (6% at 60 against 63) through
`expected_damage`, but the melee engines compute some spell damage by hand. They should take the same factor.

## Step 1: `src/wowforever/calc/ev.py`
Directly after the `level_resist_pct` function, add:
```python
def level_resist_factor(caster_level: int, target_level: int, reduction: float = 0.0) -> float:
    """Share of spell damage left after the average level resist when the `level_resistance` assumption is on,
    else 1 (#435: for spell damage the melee engines compute by hand)."""
    from wowforever.assumptions import Assumptions

    if not Assumptions.load()["level_resistance"]:
        return 1.0
    return 1.0 - level_resist_pct(caster_level, target_level, reduction) / 100.0


```

## Step 2: `src/wowforever/classes/shaman_rotation.py`
1. The import line `from wowforever.calc.ev import miss_chance` becomes
   `from wowforever.calc.ev import level_resist_factor, miss_chance`.
2. The line
```python
    hit = 1 - miss_chance(level, level + target.level_diff, stats.hit_pct) / 100
```
   becomes
```python
    hit = ((1 - miss_chance(level, level + target.level_diff, stats.hit_pct) / 100)
           * level_resist_factor(level, level + target.level_diff))      # the average level resist (#435)
```

## Step 3: `src/wowforever/classes/rogue_rotation.py`
1. The import line `from wowforever.calc.ev import miss_chance` becomes
   `from wowforever.calc.ev import level_resist_factor, miss_chance`.
2. In the `best_poisons(...)` call, the line
```python
        land=1 - miss_chance(level, level + target.level_diff, 0.0) / 100,
```
   becomes
```python
        land=((1 - miss_chance(level, level + target.level_diff, 0.0) / 100)
              * level_resist_factor(level, level + target.level_diff)),       # poisons are resisted (#435)
```

## Step 4: `src/wowforever/classes/hunter_rotation.py`
1. Add the import `from wowforever.calc.ev import level_resist_factor` directly before the line
   `from wowforever.melee_stats import MeleeStats`.
2. In the Serpent Sting block, the line
```python
                   * land_chance(a_r, target, can_dodge=False) / sting.duration)
```
   becomes
```python
                   * land_chance(a_r, target, can_dodge=False) / sting.duration
                   * level_resist_factor(stats.level, stats.level + target.level_diff))     # Nature (#435)
```
3. In the Volley block, the line
```python
                       * land_chance(a_r, target, can_dodge=False) * pack / volley.duration)
```
   becomes
```python
                       * land_chance(a_r, target, can_dodge=False) * pack / volley.duration
                       * level_resist_factor(stats.level, stats.level + target.level_diff))   # Arcane (#435)
```

Nothing else changes.

## Done when
- `tests/test_melee_spell_resist.py` passes; report other failures (score pins) without fixing them.
