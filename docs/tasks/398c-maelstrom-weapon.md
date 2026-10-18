# Task #398 (Maelstrom Weapon): a cheaper, faster Lightning Bolt from melee stacks

Make `tests/test_maelstrom.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit in this order: `src/wowforever/schema.py`, `config/shaman.toml`,
  `src/wowforever/classes/shaman.py`, `src/wowforever/classes/shaman_rotation.py`. Run the test file, then the
  fast suite once. Shaman regression pins (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, opponent kits)
  may move; Claude re-derives them.
- Before you start, the tests in `tests/test_maelstrom.py` fail.

## Why
Maelstrom Weapon: landed melee swings build up to 5 stacks; each stack cuts the next Lightning Bolt's cast time and
mana by the rank's % (20% at 5/5, so 5 stacks make it instant and free). The rank text gives no proc chance, so a
best-effort procs-per-minute guess goes in config.

## Step 1: `src/wowforever/schema.py`
In `EFFECT_KINDS`, after the `"regen_while_casting",` line, add:
```python
    "stack_pct",        # % per stack of a stacking proc (Maelstrom Weapon)
```

## Step 2: `config/shaman.toml`
At the end of the file, add:
```toml
# Maelstrom Weapon (#398): the rank text gives no proc chance. Best-effort guess: 10 procs per minute (normalized to
# the weapon's speed, so per landed swing: ppm x speed / 60), up to 5 stacks (rank text). Confidence LOW.
maelstrom_weapon = { ppm = 10.0, stacks = 5 }
```

## Step 3: `src/wowforever/classes/shaman.py`
1. At the end of `TALENT_EFFECTS` (directly before its closing `}`), add:
```python
    "Maelstrom Weapon": (
        EffectRule("stack_pct", r"Mana cost of your next Lightning Bolt spell by (\d+(?:\.\d+)?)%", ("@maelstrom",)),
    ),
```
2. Delete the `UNMODELED` line `    "Maelstrom Weapon": "proc: melee hits speed up the next spell",`.

## Step 4: `src/wowforever/classes/shaman_rotation.py`
1. In the module docstring, the two lines
```
Not modeled yet: Maelstrom Weapon's cheaper Lightning Bolt, Lightning Shield orbs (they fire when the shaman is
hit), totems.
```
   become
```
Maelstrom Weapon (#398): a cheaper, faster Lightning Bolt at the stack cap. Not modeled yet: Lightning Shield
orbs (they fire when the shaman is hit), totems.
```
2. In the `from wowforever.physical import ...` line, add `white_land_chance` to the imported names (keep them
   in alphabetical order: `Attacker, Target, white_land_chance, white_swing, yellow_attack, yellow_crit_chance`).
3. In `class EnhancementRotation`, after the `shock_mana_per_second` field, add:
```python
    maelstrom_dps: float = 0.0           # Maelstrom Weapon's Lightning Bolts, net of the swings they cost (#398)
```
4. Directly after the function-level line `    shock_dps = spell_dps` (before `nova = ...`), add:
```python
    maelstrom = 0.0
    bolt = best_rank(spells, "Lightning Bolt", level)
    per_stack = total("stack_pct", "@maelstrom")
    if bolt is not None and per_stack > 0:
        # Maelstrom Weapon (#398): landed swings build stacks; at the cap a cheaper, faster Lightning Bolt, cast
        # when it out-damages the swings its cast time left costs
        mw = c["maelstrom_weapon"]
        wf_share = c["windfury_chance"] if windfury > 0 else 0.0
        procs = mw["ppm"] / 60 * swings * weapon[2] * (1 + wf_share) * white_land_chance(attacker, target)
        left = max(0.0, 1 - per_stack * mw["stacks"] / 100)
        avg = (((bolt.min_damage + bolt.max_damage) / 2 + bolt.coefficient * spell_power)
               * (1 + total("damage_pct", "Lightning Bolt") / 100))
        gain = hit * avg * (1 + spell_crit * 0.5) - (white + windfury) * bolt.cast_time * left
        if gain > 0:
            maelstrom = procs / mw["stacks"] * gain
            spell_dps += maelstrom
            mana += procs / mw["stacks"] * cost(bolt) * left
```
5. In the final `return EnhancementRotation(...)` call, add `maelstrom_dps=maelstrom` after
   `shock_mana_per_second=shock_mana` (`shock_mana_per_second=shock_mana, maelstrom_dps=maelstrom)`).

Nothing else changes.

## Done when
- `tests/test_maelstrom.py` passes; no other new failures apart from shaman pins.
