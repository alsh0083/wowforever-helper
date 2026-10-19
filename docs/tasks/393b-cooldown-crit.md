# Task #393/#399: Rapid Killing's Rapid Fire cooldown and Holy Power's Holy Strike crit

Make `tests/test_cooldown_crit_talents.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order; run the test file at the end, then the fast suite once. Hunter and
  paladin regression pins (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, `tests/test_hunter_rotation.py`
  goldens, opponent kits) may move; Claude re-derives them.
- Before you start, most tests in `tests/test_cooldown_crit_talents.py` fail.

## Why
Rapid Killing cuts Rapid Fire's cooldown by 2 minutes (5 min to 3 min); the after-kill shot bonus stays out (it
needs kills). Holy Power raises Holy Strike's crit chance by 15%; Retribution's rotation already reads
`total("crit_chance", "Holy Strike")`. The "all other spells by 5%" part stays out (the melee row has no spells
that use it).

## Step 1: `src/wowforever/classes/hunter.py`
Add to `TALENT_EFFECTS`:
```python
    "Rapid Killing": (
        EffectRule("cooldown", r"cooldown on your Rapid Fire ability by (\d+(?:\.\d+)?) min", ("Rapid Fire",),
                   sign=-1, combine=lambda m: 60 * float(m.group(1))),
    ),
```
and delete the `UNMODELED` line for `"Rapid Killing"`.

## Step 2: `src/wowforever/classes/hunter_rotation.py`
The line
`            haste *= 1 + rapid.haste_pct / 100 * rapid.duration / rapid.cooldown`
becomes
`            haste *= 1 + rapid.haste_pct / 100 * rapid.duration / (rapid.cooldown + total("cooldown", "Rapid Fire"))`
and in the module docstring remove `Rapid Killing's cooldown cut, ` from the "Not modeled yet" list.

## Step 3: `src/wowforever/classes/paladin.py`
Add to `TALENT_EFFECTS`:
```python
    "Holy Power": (
        EffectRule("crit_chance", r"critical strike chance of your Holy Shock and Holy Strike spells by (\d+(?:\.\d+)?)%",
                   ("Holy Strike", "Holy Shock")),
    ),
```
and delete the `UNMODELED` line `    "Holy Power": "damage: Holy Shock, Holy Strike and spell crit",`.

Nothing else changes.

## Done when
- `tests/test_cooldown_crit_talents.py` passes; no other new failures apart from hunter and paladin pins.
