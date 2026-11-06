# Task #466 (part B): shaman effect rules for 1.60.1.70755

Make `tests/test_rules_70755.py -k shaman`, `tests/test_70425_shaman.py` and `tests/test_70685_pushback.py` pass.
Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/shaman.py`. No network.
- Before you start, those tests fail: Call of Thunder and Lightning Mastery have no rule, and four rules still name
  Lava Burst.
- **Run only** `.venv/Scripts/python -m pytest tests/test_rules_70755.py tests/test_70425_shaman.py tests/test_70685_pushback.py -q`.
  The shaman builds, kits and reports are rebuilt after this task; their pins may fail until then.
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.

## Why
The 3 Nov hotfixes replace Lava Burst with Call of Thunder (+5% crit for Lightning Bolt and Chain Lightning) and
rename Elemental Mastery to Lightning Mastery (Lightning Bolt only). Convection, Call of Flame, Elemental Alacrity and
Eye of the Storm no longer name Lava Burst; Eye of the Storm reads both its 70685 and its 70755 text. Lava Burst
leaves the rotation config.


## Step 1: `src/wowforever/classes/shaman.py`
Replace
```python
    "Convection": (
        EffectRule("mana_cost_pct", r"mana cost of your Shock, Lightning Bolt, Lava Burst, and Chain Lightning spells by (\d+(?:\.\d+)?)%",
                   ("Flame Shock", "Lightning Bolt", "Lava Burst", "Chain Lightning"), sign=-1),
    ),
```
with
```python
    "Convection": (
        EffectRule("mana_cost_pct", r"mana cost of your Shock, Lightning Bolt, and Chain Lightning spells by (\d+(?:\.\d+)?)%",
                   ("Flame Shock", "Lightning Bolt", "Chain Lightning"), sign=-1),
    ),
```

## Step 2: `src/wowforever/classes/shaman.py`
Replace
```python
    "Call of Flame": (
        EffectRule("damage_pct", r"Flame Shock, Fire Nova, and Lava Burst spells by (\d+(?:\.\d+)?)%", ("Flame Shock", "Lava Burst")),
        EffectRule("dot_seconds", r"duration of your Flame Shock spell by (\d+(?:\.\d+)?) sec", ("Flame Shock",)),
```
with
```python
    "Call of Flame": (
        EffectRule("damage_pct", r"Flame Shock and Fire Nova spells by (\d+(?:\.\d+)?)%", ("Flame Shock",)),
        EffectRule("dot_seconds", r"duration of your Flame Shock spell by (\d+(?:\.\d+)?) sec", ("Flame Shock",)),
```

## Step 3: `src/wowforever/classes/shaman.py`
Replace
```python
    "Elemental Alacrity": (
        EffectRule("cast_time", r"cast time of your Lightning Bolt, Chain Lightning, and Lava Burst spells by (\d+(?:\.\d+)?) sec",
                   ("Lightning Bolt", "Chain Lightning", "Lava Burst"), sign=-1),
    ),
```
with
```python
    "Elemental Alacrity": (
        EffectRule("cast_time", r"cast time of your Lightning Bolt and Chain Lightning spells by (\d+(?:\.\d+)?) sec",
                   ("Lightning Bolt", "Chain Lightning"), sign=-1),
    ),
```

## Step 4: `src/wowforever/classes/shaman.py`
Replace
```python
        EffectRule("pushback_pct",
                   r"(?:Lava Burst by |Lava Burst spells a )(\d+(?:\.\d+)?)%",
                   ("Lightning Bolt", "Chain Lightning", "Lava Burst")),
    ),
```
with
```python
        EffectRule("pushback_pct",
                   r"Lightning Bolt(?:, Chain Lightning, and Lava Burst| and Chain Lightning) spells a (\d+(?:\.\d+)?)%",
                   ("Lightning Bolt", "Chain Lightning")),
    ),
```

## Step 5: `src/wowforever/classes/shaman.py`
Replace
```python
    # Uptime-weighted cast-time cut (15 s of the 180 s cooldown); Chain Lightning's cooldown removal isn't modeled.
    "Elemental Mastery": (
        EffectRule("cast_time", r"Lava Burst by (\d+(?:\.\d+)?) sec.*Lasts (\d+(?:\.\d+)?) sec",
                   ("Lightning Bolt", "Lava Burst"), sign=-1,
                   combine=lambda m: float(m.group(1)) * float(m.group(2)) / ELEMENTAL_MASTERY_COOLDOWN),
```
with
```python
    # Uptime-weighted cast-time cut (15 s of the 180 s cooldown); Chain Lightning's cooldown removal isn't modeled.
    "Call of Thunder": (                       # Lava Burst's place since the 3 Nov hotfixes (#466)
        EffectRule("crit_chance", r"Lightning Bolt and Chain Lightning spells by (\d+(?:\.\d+)?)%",
                   ("Lightning Bolt", "Chain Lightning")),
    ),
    "Lightning Mastery": (                     # Elemental Mastery, renamed (#466)
        EffectRule("cast_time", r"Lightning Bolt spell by (\d+(?:\.\d+)?) sec.*Lasts (\d+(?:\.\d+)?) sec",
                   ("Lightning Bolt",), sign=-1,
                   combine=lambda m: float(m.group(1)) * float(m.group(2)) / ELEMENTAL_MASTERY_COOLDOWN),
```

## Step 6: `src/wowforever/classes/shaman.py`
Replace
```python
    "Earthbound": "control: Earthbind Totem roots 5 s",
    "Lava Burst": "grants_spell",
    # Enhancement
    "Earth's Grasp": "utility: Stoneclaw health, Earthbind radius",
```
with
```python
    "Earthbound": "control: Earthbind Totem roots 5 s",
   # Enhancement
    "Earth's Grasp": "utility: Stoneclaw health, Earthbind radius",
```

## Step 7: `src/wowforever/classes/shaman.py`
Replace
```python
    "dots": ("Flame Shock",),
    "cooldowns": ("Lava Burst", "Chain Lightning"),
    "fillers": ("Lightning Bolt",),
```
with
```python
    "dots": ("Flame Shock",),
    "cooldowns": ("Chain Lightning",),             # Lava Burst left with the 3 Nov hotfixes (#466)
    "fillers": ("Lightning Bolt",),
```

## Step 8: `src/wowforever/classes/shaman.py`
Replace
```python
    "fillers": ("Lightning Bolt",),
    # Lava Burst's own effect 1 (SpellEffect 408490, 1.60.1.70425): +20% damage with Flame Shock up (#384)
    "dot_bonus": {"Lava Burst": ("Flame Shock", 20.0)},
}
```
with
```python
    "fillers": ("Lightning Bolt",),
    # a spell's bonus while a DoT is up (#384); Lava Burst's +20% with Flame Shock was the only one
    "dot_bonus": {},
}
```
