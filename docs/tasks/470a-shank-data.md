# Task #470 (part A): Shank in the rogue's spells, with the Energy it gives back

Make `tests/test_shank_data.py` and `tests/test_poison_data.py` pass without breaking the rest of the fast suite.
Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/schema.py`, `src/wowforever/normalize_spells.py` and
  `src/wowforever/classes/rogue.py`. No network.
- Before you start, those two test files fail (no `energy_gain`, no Shank in `EXTRA_SPELLS`).
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.
- Run `.venv/Scripts/python -m pytest tests/test_shank_data.py tests/test_poison_data.py -q` at the end, then the
  fast suite once.

## Why
Shank (1329283, 1329549) is every rogue's off-hand strike since the 3 Nov hotfixes, and the spells normalizer drops it:
- its skill-line row has BaseLevel 0, so its learn level is SpellLevel (24, 44);
- its damage is a percent-weapon effect alone (31: 50%), with no 58/121 strike next to it;
- the Energy it restores (effect 30, EffectMiscValue_0 3: 15 and 25) has no field.


## Step 1: `src/wowforever/schema.py`
Replace
```python
    combo_points: int = 0              # combo points awarded (effect 30 with EffectMiscValue_0 == 4)
    damage_shield: float = 0.0         # damage per melee hit taken (aura 15: Thorns), base points (#261)
```
with
```python
    combo_points: int = 0              # combo points awarded (effect 30 with EffectMiscValue_0 == 4)
    energy_gain: int = 0               # Energy the spell restores (effect 30 with EffectMiscValue_0 == 3: Shank, #470)
    damage_shield: float = 0.0         # damage per melee hit taken (aura 15: Thorns), base points (#261)
```

## Step 2: `src/wowforever/normalize_spells.py`
Replace
```python

    for spell_id, name in extra_spells.items():
```
with
```python

    kept = {spell_id for _, _, spell_id in trainable}
    for spell_id, name in extra_spells.items():
```

## Step 3: `src/wowforever/normalize_spells.py`
Replace
```python
        level_row = levels.get(spell_id)
        if spell_id not in seen and level_row is not None and int(_f(level_row["BaseLevel"])) > 0:
            seen.add(spell_id)
            trainable.append((name, int(_f(level_row["BaseLevel"])), spell_id))

```
with
```python
        level_row = levels.get(spell_id)
        # BaseLevel, or SpellLevel when BaseLevel is 0: Shank is on a skill line with BaseLevel 0 (#470)
        level = int(_f(level_row["BaseLevel"])) or int(_f(level_row["SpellLevel"])) if level_row is not None else 0
        if spell_id not in kept and level > 0:
            kept.add(spell_id)
            trainable.append((name, level, spell_id))

```

## Step 4: `src/wowforever/normalize_spells.py`
Replace
```python
    combo_points = int(_f(combo_row["EffectBasePointsF"])) if combo_row is not None else 0
    per_combo_point = _f(damage["EffectPointsPerResource"]) if damage is not None else 0.0
```
with
```python
    combo_points = int(_f(combo_row["EffectBasePointsF"])) if combo_row is not None else 0
    energy_row = next((e for e in effects
                       if e["Effect"] == str(EFFECT_COMBO_POINTS) and e["EffectMiscValue_0"] == "3"), None)   # energize Energy
    energy_gain = int(_f(energy_row["EffectBasePointsF"])) if energy_row is not None else 0
    per_combo_point = _f(damage["EffectPointsPerResource"]) if damage is not None else 0.0
```

## Step 5: `src/wowforever/normalize_spells.py`
Replace
```python
        per_combo_point=per_combo_point, periodic_per_combo_point=periodic_per_combo_point,
        combo_points=combo_points, haste_pct=haste_pct,
        ranged_attack_power=ranged_attack_power,
```
with
```python
        per_combo_point=per_combo_point, periodic_per_combo_point=periodic_per_combo_point,
        combo_points=combo_points, energy_gain=energy_gain, haste_pct=haste_pct,
        ranged_attack_power=ranged_attack_power,
```

## Step 6: `src/wowforever/normalize_spells.py`
Replace
```python
    if strike is None:
        return 0, 0.0, False, 0.0
    pct_row = next((e for e in strike_rows if e["Effect"] == str(EFFECT_WEAPON_PCT)), None)
```
with
```python
    if strike is None:
        # a percent-weapon effect alone is a strike too: Shank, 50% of the off-hand weapon (#470)
        pct_only = next((e for e in effects if e["Effect"] == str(EFFECT_WEAPON_PCT)), None)
        return (1, 0.0, False, _f(pct_only["EffectBasePointsF"])) if pct_only is not None else (0, 0.0, False, 0.0)
    pct_row = next((e for e in strike_rows if e["Effect"] == str(EFFECT_WEAPON_PCT)), None)
```

## Step 7: `src/wowforever/classes/rogue.py`
Replace
```python
    25349: "Deadly Poison",
}
```
with
```python
    25349: "Deadly Poison",
    # Shank (#470): baseline since the 3 Nov hotfixes, not on a talent skill line; rank 2 at 44
    1329283: "Shank", 1329549: "Shank",
}
```
