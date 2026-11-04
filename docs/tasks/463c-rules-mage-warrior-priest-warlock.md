# Task #463 (part C): mage, warrior, priest and warlock effect rules for 1.60.1.70755

Make `tests/test_rules_70755.py -k "mage or warrior or priest or warlock"` pass. Do not edit the tests or anything under
`tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/mage.py`, `warrior.py`, `priest.py` and `warlock.py`. No network.
- Before you start, those tests fail with talents "in neither TALENT_EFFECTS nor UNMODELED" or "not a talent in the dataset".
- **Run only** `.venv/Scripts/python -m pytest tests/test_rules_70755.py -q -k "mage or warrior or priest or warlock"`.
  Do not run the fast suite: it still reads build 1.60.1.70425, which these rules no longer match. That is expected
  until the pin moves (#463).
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.

## Why
The 70685 and 70707 talent changes (#443, #454) and Blizzard's 2 Nov notes (#465, #469):
- **Mage:** Accelerant and Precision replace Improved Fireball, Elemental Precision and Arcane Focus. Piercing Ice is gone.
- **Warrior:** Improved Whirlwind replaces Raging Blows, and Improved Slam's text changed.
- **Priest:** Holy Binding replaces Binding Heal.
- **Warlock:** Improved Drains covers Drain Mana instead of Wrack.

## Step 1: `src/wowforever/classes/mage.py`
Replace
```python
        EffectRule("regen_while_casting", r"Allows (\d+(?:\.\d+)?)% of your Mana regeneration", ("all",)),
    ),
    "Arcane Focus": (
        EffectRule("hit_chance", r"chance to hit with Arcane spells by (\d+(?:\.\d+)?)%", ("arcane",)),
    ),
```
with
```python
        EffectRule("regen_while_casting", r"Allows (\d+(?:\.\d+)?)% of your Mana regeneration", ("all",)),
    ),
```

## Step 2: `src/wowforever/classes/mage.py`
Replace
```python
    ),
    "Improved Fireball": (
        EffectRule("cast_time",
```
with
```python
    ),
    "Accelerant": (
        EffectRule("cast_time",
```

## Step 3: `src/wowforever/classes/mage.py`
Replace
```python
        EffectRule("cast_time",
                   r"casting time of your Fireball and Frostfire Bolt spells by (\d+(?:\.\d+)?) sec",
                   ("Fireball", "Frostfire Bolt"), sign=-1),
    ),
```
with
```python
        EffectRule("cast_time",
                   r"casting time of your Fireball, Frostfire Bolt, and Arcane Wrath spells by (\d+(?:\.\d+)?) sec",
                   ("Fireball", "Frostfire Bolt", "Arcane Wrath"), sign=-1),
    ),
```

## Step 4: `src/wowforever/classes/mage.py`
Replace
```python
    ),
    "Piercing Ice": (
        EffectRule("damage_pct", r"damage done by your Frost spells by (\d+(?:\.\d+)?)%", ("frost",)),
    ),
    "Improved Frostbolt": (
```
with
```python
    ),
    "Improved Frostbolt": (
```

## Step 5: `src/wowforever/classes/mage.py`
Replace
```python
    ),
    "Elemental Precision": (
        EffectRule("hit_chance", r"chance to hit with Frost and Fire spells by (\d+(?:\.\d+)?)%",
                   ("fire", "frost")),
    ),
```
with
```python
    ),
    "Precision": (
        EffectRule("hit_chance", r"chance to hit with all spells by (\d+(?:\.\d+)?)%", ("all",)),
    ),
```

## Step 6: `src/wowforever/classes/warrior.py`
Replace
```python
    ),
    "Raging Blows": (
        EffectRule("rage_cost", r"Rage cost of your Cleave and Whirlwind abilities by (\d+(?:\.\d+)?)", ("Cleave", "Whirlwind"), sign=-1),
    ),
```
with
```python
    ),
    "Improved Whirlwind": (
        EffectRule("cooldown", r"cooldown of your Whirlwind ability by (\d+(?:\.\d+)?) sec", ("Whirlwind",), sign=-1),
    ),
```

## Step 7: `src/wowforever/classes/warrior.py`
Replace
```python
    "Improved Slam": (
        EffectRule("cooldown", r"Slam's cooldown is reduced by (\d+(?:\.\d+)?) sec", ("Slam",), sign=-1),
    ),
```
with
```python
    "Improved Slam": (
        EffectRule("cooldown", r"cooldown of your Slam ability by (\d+(?:\.\d+)?) sec", ("Slam",), sign=-1),
    ),
```

## Step 8: `src/wowforever/classes/warrior.py`
Replace
```python
    "Death Wish": "grants_spell",
    "Improved Intercept": "mobility: Intercept cooldown -10 s",
```
with
```python
    "Death Wish": "grants_spell",
    "Reckless Swings": "grants_spell",
    "Improved Intercept": "mobility: Intercept cooldown -10 s",
```

## Step 9: `src/wowforever/classes/priest.py`
Replace
```python
    "Improved Healing": "resource: cheaper heals",
    "Binding Heal": "grants_spell",
    "Litany of Light": "resource: mana back when alternating heals",
```
with
```python
    "Improved Healing": "resource: cheaper heals",
    "Holy Binding": "healing: Flash Heal on others heals the Priest for 50%",
    "Litany of Light": "resource: mana back when alternating heals",
```

## Step 10: `src/wowforever/classes/warlock.py`
Replace
```python
    "Improved Drains": (
        EffectRule("damage_pct", r"Drain Life, Drain Soul, and Wrack spells by (\d+(?:\.\d+)?)%",
                   ("Drain Life", "Drain Soul", "Wrack")),
    ),
```
with
```python
    "Improved Drains": (
        EffectRule("damage_pct", r"Drain Life, Drain Soul, and Drain Mana spells by (\d+(?:\.\d+)?)%",
                   ("Drain Life", "Drain Soul")),
    ),
```
