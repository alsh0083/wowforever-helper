# Task #391 (part 6): Slam with Improved Slam

Make `tests/test_slam.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/classes/warrior.py`, then `src/wowforever/classes/warrior_rotation.py`. Run
  the test file, then the fast suite once. Warrior regression pins may move; Claude re-derives them.
- Before you start, the tests in `tests/test_slam.py` fail.

## Why
Improved Slam: Slam no longer delays the melee swing and its cooldown is 3 s shorter. With it, Slam (weapon damage +
87, 15 Rage) is a cooldown ability like Whirlwind; without it Slam would delay swings, so it stays out.

## Step 1: `src/wowforever/classes/warrior.py`
Add to `TALENT_EFFECTS`:
```python
    "Improved Slam": (
        EffectRule("cooldown", r"Slam's cooldown is reduced by (\d+(?:\.\d+)?) sec", ("Slam",), sign=-1),
    ),
```
and delete the `UNMODELED` line `    "Improved Slam": "melee damage: faster Slam that doesn't reset swings",`.

## Step 2: `src/wowforever/classes/warrior_rotation.py`
1. `    names = ("Mortal Strike", "Bloodthirst", "Whirlwind") + (("Thunder Clap",) if pack > 1 else ())` becomes
   `    names = ("Mortal Strike", "Bloodthirst", "Whirlwind", "Slam") + (("Thunder Clap",) if pack > 1 else ())`
2. The plan comprehension
```python
    plan = [s for s in map(learned, names)
            if s is not None and s.cooldown > 0
            and (s.name not in ("Mortal Strike", "Bloodthirst") or taken(s.name))]
```
   becomes
```python
    plan = [replace(s, cooldown=s.cooldown + total("cooldown", s.name)) for s in map(learned, names)
            if s is not None and s.cooldown > 0
            and (s.name not in ("Mortal Strike", "Bloodthirst") or taken(s.name))
            and (s.name != "Slam" or taken("Improved Slam"))]      # Slam only once it stops delaying swings (#391)
```
3. In the module docstring, `Not modeled yet: Slam and Rage from damage taken.` becomes
   `Slam joins with Improved Slam (#391). Not modeled yet: Rage from damage taken.` (keep lines under 110).

Nothing else changes.

## Done when
- `tests/test_slam.py` passes; no other new failures apart from warrior pins.
