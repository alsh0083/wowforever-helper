# Task #464: rogue effect rules for 1.60.1.70755

Make `tests/test_rules_70755.py -k rogue` pass. Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/rogue.py`. No network.
- Before you start, the test fails with talents "in neither TALENT_EFFECTS nor UNMODELED" or "not a talent in the dataset".
- **Run only** `.venv/Scripts/python -m pytest tests/test_rules_70755.py -q -k rogue`. Do not run the fast suite: it still
  reads build 1.60.1.70425, which these rules no longer match. That is expected until the pin moves (#463).
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.

## Why
Build 1.60.1.70755 with the 3 Nov hotfixes reworks the rogue trees (Blizzard's 2 Nov notes):
- Removed: Murder, Quietus, Cutthroat, Thousand Cuts, Improved Distract.
- Renamed: Improved Eviscerate is now Coup de Grace, Improved Sinister Strike is now Efficient Strikes.
- Aggression no longer covers Backstab.
- The new Shank and Poised talents stay unmodeled until #470.

## Step 1: `src/wowforever/classes/rogue.py`
Replace
```python

from wowforever.classes import EffectRule, TraitLayout, TreeBand, below_health

```
with
```python

from wowforever.classes import EffectRule, TraitLayout, TreeBand

```

## Step 2: `src/wowforever/classes/rogue.py`
Replace
```python
                   ("@finisher",)),
    ),
    "Murder": (
        EffectRule("damage_pct", r"damage dealt by (\d+(?:\.\d+)?)%", ("@humanoid",)),
    ),
```
with
```python
                   ("@finisher",)),
    ),
```

## Step 3: `src/wowforever/classes/rogue.py`
Replace
```python
    # Combat
    "Improved Eviscerate": (
        EffectRule("damage_pct", r"Eviscerate ability by (\d+(?:\.\d+)?)%", ("Eviscerate",)),
```
with
```python
    # Combat
    "Coup de Grace": (
        # its Death Mark part waits for Death Mark in the engine (#470)
        EffectRule("damage_pct", r"Eviscerate ability by (\d+(?:\.\d+)?)%", ("Eviscerate",)),
```

## Step 4: `src/wowforever/classes/rogue.py`
Replace
```python
    ),
    "Improved Sinister Strike": (
        EffectRule("energy_cost",
```
with
```python
    ),
    "Efficient Strikes": (
        EffectRule("energy_cost",
```

## Step 5: `src/wowforever/classes/rogue.py`
Replace
```python
        EffectRule("energy_cost",
                   r"Energy cost of your Sinister Strike ability by (\d+(?:\.\d+)?)",
                   ("Sinister Strike",), sign=-1),
    ),
```
with
```python
        EffectRule("energy_cost",
                   r"Energy cost of your Sinister Strike and Hemorrhage abilities by (\d+(?:\.\d+)?)",
                   ("Sinister Strike", "Hemorrhage"), sign=-1),
    ),
```

## Step 6: `src/wowforever/classes/rogue.py`
Replace
```python
        EffectRule("damage_pct", r"damage of your .* abilities by (\d+(?:\.\d+)?)%",
                   ("Sinister Strike", "Backstab", "Eviscerate")),
    ),
```
with
```python
        EffectRule("damage_pct", r"damage of your .* abilities by (\d+(?:\.\d+)?)%",
                   ("Sinister Strike", "Eviscerate")),
    ),
```

## Step 7: `src/wowforever/classes/rogue.py`
Replace
```python
        EffectRule("armor_pen", r"ignore (\d+(?:\.\d+)?)% of your target's Armor", ("all",)),
    ),
    "Quietus": (
        EffectRule("damage_pct",
                   r"abilities cause (\d+(?:\.\d+)?)% more damage against targets below (\d+(?:\.\d+)?)% health",
                   ("Sinister Strike", "Ghostly Strike", "Hemorrhage"), combine=below_health),
    ),
```
with
```python
        EffectRule("armor_pen", r"ignore (\d+(?:\.\d+)?)% of your target's Armor", ("all",)),
    ),
```

## Step 8: `src/wowforever/classes/rogue.py`
Replace
```python
    "Improved Kidney Shot": "control: more damage to Kidney Shot stuns",
    "Venom": "grants_spell",
    # Combat
```
with
```python
    "Improved Kidney Shot": "control: more damage to Kidney Shot stuns",
    "Venom": "proc: Shank raises poison damage and application chance; Shank not in the engine yet (#470)",
    "Blood Splatter": "dot: longer Rupture and Garrote; the rotation casts neither for damage (#392)",
    # Combat
```

## Step 9: `src/wowforever/classes/rogue.py`
Replace
```python
    "Adrenaline Rush": "grants_spell",
    # Subtlety
```
with
```python
    "Adrenaline Rush": "grants_spell",
    "Composure": "resource: bigger Poised discount; Poised not in the engine yet (#470)",
    "Flash of Steel": "resource: more Shank Energy, shorter Shank cooldown; Shank not in the engine yet (#470)",
    # Subtlety
```

## Step 10: `src/wowforever/classes/rogue.py`
Replace
```python
    "Ghostly Strike": "grants_spell",
    "Improved Distract": "utility: larger Distract radius, less detection of distracted enemies",
    "Heightened Senses": "stealth: better Stealth detection, less hit by spells and ranged",
```
with
```python
    "Ghostly Strike": "grants_spell",
    "Heightened Senses": "stealth: better Stealth detection, less hit by spells and ranged",
```

## Step 11: `src/wowforever/classes/rogue.py`
Replace
```python
    "Hemorrhage": "grants_spell",
    "Cutthroat": "stealth: Backstab can enable Ambush without Stealth",
    "Thousand Cuts": "resource: Rupture ticks cut Hemorrhage/Backstab cost; Rupture loses to Eviscerate, so 0 (#392)",
}
```
with
```python
    "Hemorrhage": "grants_spell",
    "Quick Getaway": "control: one more Sapped target, speed after Sap",
    "Boot Knife": "resource: Shank adds Combo Points; Shank not in the engine yet (#470)",
    "Death Mark": "grants_spell",
}
```
