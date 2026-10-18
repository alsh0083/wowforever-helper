# Task #393 (part B): hunter mana regen while casting

Make `tests/test_hunter_regen.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `config/melee.toml`, then `src/wowforever/classes/hunter.py`, then
  `src/wowforever/classes/hunter_rotation.py`. Run the test file, then the fast suite once. Hunter regression pins
  (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, opponent kits) may move; Claude re-derives them.
- Before you start, the tests in `tests/test_hunter_regen.py` fail. Part A already put Spirit on the melee rows.

## Why
A hunter shoots all fight, so its Spirit regen stops (the five-second rule), except the share that Bestial Discipline
(50%) and Rapid Recuperation (50% while Serpent Sting is up) keep going. Regen per second is the Classic hunter
formula, (15 + Spirit / 5) per 2 s tick. The rotation's mana use drops by that share of regen.

## Step 1: `config/melee.toml`
In the `[hunter]` section, after `uses_mana = true`, add:
```toml
# Spirit regen outside the five-second rule, per 2 s tick: regen_base + spirit / regen_spirit_div (Classic, #393)
regen_base = 15
regen_spirit_div = 5
```

## Step 2: `src/wowforever/classes/hunter.py`
Add to `TALENT_EFFECTS` (if `"Bestial Discipline"` already has a rule tuple, add the rule to it; otherwise add the
entry):
```python
    "Bestial Discipline": (
        EffectRule("regen_while_casting", r"allows (\d+(?:\.\d+)?)% of your Mana regeneration to continue while casting",
                   ("all",)),
    ),
    "Rapid Recuperation": (
        EffectRule("regen_while_casting", r"allows (\d+(?:\.\d+)?)% of your Mana Regeneration to continue while casting",
                   ("@sting",)),
    ),
```
and delete their two `UNMODELED` lines.

## Step 3: `src/wowforever/classes/hunter_rotation.py`
Directly before the final `    return HunterRotation(...)` statement add:
```python
    # the share of Spirit regen that keeps going while shooting (Bestial Discipline, Rapid Recuperation, #393)
    m = load_toml(MELEE)["hunter"]
    share = total("regen_while_casting", "all")
    if learned("Serpent Sting") is not None:
        share += total("regen_while_casting", "@sting")
    regen = min(100.0, share) / 100 * (m["regen_base"] + stats.spirit / m["regen_spirit_div"]) / 2
    mana_r, mana_m = mana_r - regen, mana_m - regen
```
(`MELEE` is the module's existing path to `config/melee.toml`, and `load_toml` is already imported.)

Nothing else changes.

## Done when
- `tests/test_hunter_regen.py` passes; no other new failures apart from hunter pins.
