# Task #465 (part A): Improved Whirlwind's extra damage to the closest enemy

Make `tests/test_improved_whirlwind.py` pass, with `tests/test_warrior_aoe.py` and `tests/test_rules_70755.py -k warrior`.
Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/warrior.py` and `src/wowforever/classes/warrior_rotation.py`.
  No network.
- Before you start, those tests fail on the Improved Whirlwind rule and the Whirlwind ratios.
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.
- Run `.venv/Scripts/python -m pytest tests/test_improved_whirlwind.py tests/test_warrior_aoe.py tests/test_rules_70755.py -q`
  at the end, then the fast suite once.

## Why
1.60.1.70755's Improved Whirlwind also "increases the damage it deals to the closest enemy by 15%/30%". The rule
read only the cooldown, so Whirlwind dealt the same to every mob and too little on one target.


## Step 1: `src/wowforever/classes/warrior.py`
Replace
```python
        EffectRule("cooldown", r"cooldown of your Whirlwind ability by (\d+(?:\.\d+)?) sec", ("Whirlwind",), sign=-1),
    ),
```
with
```python
        EffectRule("cooldown", r"cooldown of your Whirlwind ability by (\d+(?:\.\d+)?) sec", ("Whirlwind",), sign=-1),
        EffectRule("damage_pct", r"damage it deals to the closest enemy by (\d+(?:\.\d+)?)%", ("@closest_Whirlwind",)),
    ),
```

## Step 2: `src/wowforever/classes/warrior_rotation.py`
Replace
```python
        n = targets(spell)
        rage -= rate * cost(spell)
```
with
```python
        n = targets(spell)
        closest = 1 + total("damage_pct", f"@closest_{name}") / 100     # Improved Whirlwind's closest enemy (#465)
        rage -= rate * cost(spell)
```

## Step 3: `src/wowforever/classes/warrior_rotation.py`
Replace
```python
        rage -= rate * cost(spell)
        yellow += rate * strike(spell) * n
        parts.append((name, rate * strike(spell) * n))
        single, attacks = single + rate * strike(spell), attacks + rate
        crits += rate * n * land_chance(attacker, target) * yellow_crit_chance(attacker, target,
```
with
```python
        rage -= rate * cost(spell)
        yellow += rate * strike(spell) * (n - 1 + closest)
        parts.append((name, rate * strike(spell) * (n - 1 + closest)))
        single, attacks = single + rate * strike(spell) * closest, attacks + rate
        crits += rate * n * land_chance(attacker, target) * yellow_crit_chance(attacker, target,
```
