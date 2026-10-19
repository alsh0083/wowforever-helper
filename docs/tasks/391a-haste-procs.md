# Task #391/#393 (part 1): Flurry (warrior) and Deadly Aspects (hunter)

Make `tests/test_haste_procs.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order; run the test file at the end, then the fast suite once. Warrior and
  hunter regression pins (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, `tests/test_hunter_rotation.py`
  goldens, opponent kits) may move; Claude re-derives them.
- Before you start, most tests in `tests/test_haste_procs.py` fail.

## Why
Both talents raise attack speed for a while after a proc. The Enhancement shaman already models Flurry as an
average uptime (`shaman_rotation.py`); the warrior and hunter get the same treatment.

## Step 1: warrior
1. `config/warrior.toml`: append
```toml
# Flurry lasts this many swings after a crit (rank text: "your next 3 swings", #391)
flurry_swings = 3
```
2. `src/wowforever/classes/warrior.py`: add to `TALENT_EFFECTS`:
```python
    "Flurry": (
        EffectRule("haste_pct", r"attack speed by (\d+(?:\.\d+)?)% for your next 3 swings", ("@flurry",)),
    ),
```
   and delete the `UNMODELED` line for `"Flurry"`.
3. `src/wowforever/classes/warrior_rotation.py`:
   - The line `    swings = 1 / weapon[2]` becomes:
```python
    haste = 1.0
    if taken("Flurry"):      # faster swings while any of the last 3 swings critted (#391)
        crit = yellow_crit_chance(attacker, target)
        haste += total("haste_pct", "@flurry") / 100 * (1 - (1 - crit) ** c["flurry_swings"])
    swings = haste / weapon[2]
```
   - In the module docstring, `Not modeled yet: Fury dual wield and Bloodthirst, Flurry, Execute below 20%,` becomes
     `Flurry is an average uptime (#391). Not modeled yet: Fury dual wield and Bloodthirst, Execute below 20%,`.

## Step 2: hunter
1. `src/wowforever/classes/hunter.py`: add to `TALENT_EFFECTS`:
```python
    "Deadly Aspects": (
        EffectRule("proc_chance", r"Auto Shot has a (\d+(?:\.\d+)?)% chance", ("@deadly_aspects",)),
        EffectRule("haste_pct", r"ranged attack speed by (\d+(?:\.\d+)?)% for", ("@deadly_aspects",)),
        EffectRule("duration", r"ranged attack speed by \d+(?:\.\d+)?% for (\d+(?:\.\d+)?) sec", ("@deadly_aspects",)),
    ),
```
   and delete the `UNMODELED` line for `"Deadly Aspects"`.
2. `src/wowforever/classes/hunter_rotation.py`: directly after the two lines
```python
        if rapid is not None:
            haste *= 1 + rapid.haste_pct / 100 * rapid.duration / rapid.cooldown
```
   add:
```python
        if taken("Deadly Aspects") and learned("Aspect of the Hawk") is not None:
            # each Auto Shot may haste the next window; uptime from the shots in one window (#393)
            shots = total("duration", "@deadly_aspects") * haste / speed
            uptime = 1 - (1 - total("proc_chance", "@deadly_aspects") / 100) ** shots
            haste *= 1 + total("haste_pct", "@deadly_aspects") / 100 * uptime
```
   - In the module docstring, remove `Deadly Aspects procs, ` from the "Not modeled yet" list.

Nothing else changes.

## Done when
- `tests/test_haste_procs.py` passes (4 tests); no other new failures apart from warrior and hunter pins.
