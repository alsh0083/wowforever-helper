# Task #388: Aspect of the Hawk's ranged attack power

Make `tests/test_hawk.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order. Step 3 runs a tool that rewrites `data/datasets/1.60.1.70425.json`; run it
  exactly once, after steps 1-3's edits. Hunter regression pins (`tests/test_dungeon_mana.py`,
  `tests/test_kit_stats.py`, opponent kits) may move; Claude re-derives them.
- Before you start, all 3 tests in `tests/test_hawk.py` fail.

## Why
Forever's Aspect of the Hawk gives ranged attack power (aura 124: 120 at rank 7), and a ranged hunter keeps it up,
but the spell data has no field for it and the rotation never adds it.

## Step 1: `src/wowforever/schema.py`
In `class SpellRank`, directly after the line
`    haste_pct: float = 0.0             # melee haste aura (aura 319) base points`
add
`    ranged_attack_power: float = 0.0   # ranged attack power aura (aura 124) base points (Aspect of the Hawk, #388)`

## Step 2: `src/wowforever/normalize_spells.py`
1. After the `AURA_SLOW = 33 ...` constant line add
   `AURA_RANGED_ATTACK_POWER = 124  # ranged attack power (Aspect of the Hawk, #388)`
2. Directly after the line `    haste_pct = _f(haste_row["EffectBasePointsF"]) if haste_row is not None else 0.0` add:
```python
    rap_row = next((e for e in effects
                    if e["Effect"] == str(EFFECT_AURA) and int(e["EffectAura"]) == AURA_RANGED_ATTACK_POWER), None)
    ranged_attack_power = _f(rap_row["EffectBasePointsF"]) if rap_row is not None else 0.0
```
3. In the `SpellRank(...)` call that passes `haste_pct=haste_pct,`, add `ranged_attack_power=ranged_attack_power,`
   right after `haste_pct=haste_pct,`.

## Step 3: `tools/refresh_periodic.py`, then run it
1. `FIELDS = ("periodic_damage", "periodic_coefficient", "tick_period")` becomes
   `FIELDS = ("periodic_damage", "periodic_coefficient", "tick_period", "ranged_attack_power")`
2. `diff = {f: (spell.get(f), getattr(new, f)) for f in FIELDS if spell.get(f) != getattr(new, f)}` becomes
   `diff = {f: (spell.get(f), getattr(new, f)) for f in FIELDS if spell.get(f, 0.0) != getattr(new, f)}`
3. In the module docstring, after the paragraph ending "...as 0 damage.", add the line
   `#388 adds ranged_attack_power (Aspect of the Hawk); spells without it keep no key.`
Then run `.venv/Scripts/python tools/refresh_periodic.py 1.60.1.70425` once. It prints the 7 Aspect of the Hawk ranks.

## Step 4: `src/wowforever/classes/hunter_rotation.py`
Directly after the line that starts `        rap = stats.ranged_attack_power + int_ap + 2 * extra_agi`, add:
```python
        hawk = learned("Aspect of the Hawk")       # kept up while shooting (#388)
        rap += hawk.ranged_attack_power if hawk is not None else 0.0
```

Nothing else changes.

## Done when
- `tests/test_hawk.py` passes (3 tests); `git diff data/datasets` adds only `ranged_attack_power` lines to the 7
  Aspect of the Hawk ranks; no other new failures apart from hunter pins.
