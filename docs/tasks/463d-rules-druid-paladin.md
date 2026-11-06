# Task #463 (part D): druid and paladin effect rules and the druid crit auras for 1.60.1.70755

Make `tests/test_rules_70755.py -k "druid or paladin"` pass. Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/druid.py`, `src/wowforever/classes/paladin.py` and
  `config/group_buffs.toml`. No network.
- Before you start, those tests fail with talents "in neither TALENT_EFFECTS nor UNMODELED" or "not a talent in the dataset".
- **Run only** `.venv/Scripts/python -m pytest tests/test_rules_70755.py -q -k "druid or paladin"`. Do not run the fast
  suite: it still reads build 1.60.1.70425, which these rules no longer match. That is expected until the pin moves (#463).
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.

## Why
The 30 Oct druid and paladin reworks (#455) and Blizzard's 2 Nov notes (#468, #469):
- **Druid:** Naturalist also speeds up Wild Growth. Bloom, Lacerate and Predatory Discipline are new. Berserk, Gift of
  the Earthmother and Improved Shifting Power are gone.
- **Paladin:** Conviction, Two-Handed Weapon Specialization and Holy Power have new text. Six talents are new, and five
  are removed.
- **Group buffs:** Leader of the Pack and Moonkin Aura give all crit again (aura 290) and no longer stack with each other.

## Step 1: `src/wowforever/classes/druid.py`
Replace
```python
    "Naturalist": (
        EffectRule("cast_time", r"cast time of your Healing Touch spell by (\d+(?:\.\d+)?) sec", ("Healing Touch",), sign=-1),
        EffectRule("damage_pct", r"increases all damage you deal by (\d+(?:\.\d+)?)%", ("all",)),
```
with
```python
    "Naturalist": (
        EffectRule("cast_time", r"cast time of your Healing Touch and Wild Growth spells by (\d+(?:\.\d+)?) sec",
                   ("Healing Touch", "Wild Growth"), sign=-1),
        EffectRule("damage_pct", r"increases all damage you deal by (\d+(?:\.\d+)?)%", ("all",)),
```

## Step 2: `src/wowforever/classes/druid.py`
Replace
```python
        EffectRule("duration", r"your Regrowth spell by (\d+(?:\.\d+)?) sec", ("Regrowth",)),
    ),
    "Gift of the Earthmother": (
        EffectRule("gcd", r"global cooldown by (\d+(?:\.\d+)?) seconds", ("Rejuvenation", "Swiftmend", "Wild Growth"), sign=-1),
    ),
```
with
```python
        EffectRule("duration", r"your Regrowth spell by (\d+(?:\.\d+)?) sec", ("Regrowth",)),
    ),
```

## Step 3: `src/wowforever/classes/druid.py`
Replace
```python
    "Primal Bite": "grants_spell",
    "Improved Shifting Power": "resource: Shifting Power cooldown -8 s",
    "Natural Reaction": "defensive: +5% dodge, Rage on dodge",
```
with
```python
    "Primal Bite": "grants_spell",
    "Lacerate": "grants_spell",
    "Predatory Discipline": "damage: Ferocious Bite keeps its excess-Energy bonus without spending the Energy; not modeled yet (#468)",
    "Natural Reaction": "defensive: +5% dodge, Rage on dodge",
```

## Step 4: `src/wowforever/classes/druid.py`
Replace
```python
    "Natural Reaction": "defensive: +5% dodge, Rage on dodge",
    "Berserk": "damage: builder crit averaged in druid_rotation (#397); its cleave is bear-only Primal Bite (#431)",
    # Restoration
```
with
```python
    "Natural Reaction": "defensive: +5% dodge, Rage on dodge",
    # Restoration
```

## Step 5: `src/wowforever/classes/druid.py`
Replace
```python
    # Restoration
    "Furor": "resource: Energy kept across shifts plus 10/s outside (no more than regen), so no powershift gain (#431)",
```
with
```python
    # Restoration
    "Bloom": "healing: Spirit-based heal when Rejuvenation or Regrowth runs its full duration; not modeled yet (#468)",
    "Furor": "resource: Energy kept across shifts plus 10/s outside (no more than regen), so no powershift gain (#431)",
```

## Step 6: `src/wowforever/classes/paladin.py`
Replace
```python
    "Conviction": (
        EffectRule("crit_chance", r"critical strike with melee attacks by (\d+(?:\.\d+)?)%", ("all",)),
    ),
```
with
```python
    "Conviction": (
        EffectRule("crit_chance", r"critical strike with all spells and attacks by (\d+(?:\.\d+)?)%", ("all",)),
    ),
```

## Step 7: `src/wowforever/classes/paladin.py`
Replace
```python
    "Two-Handed Weapon Specialization": (
        EffectRule("damage_pct", r"damage you deal with two-handed melee weapons by (\d+(?:\.\d+)?)%", ("@two_hand",)),
    ),
```
with
```python
    "Two-Handed Weapon Specialization": (
        EffectRule("damage_pct", r"Physical and Holy damage you deal by (\d+(?:\.\d+)?)%, and reduces all threat",
                   ("@two_hand",)),
    ),
```

## Step 8: `src/wowforever/classes/paladin.py`
Replace
```python
    "Holy Power": (
        EffectRule("crit_chance", r"critical strike chance of your Holy Shock and Holy Strike spells by (\d+(?:\.\d+)?)%",
                   ("Holy Strike", "Holy Shock")),
    ),
```
with
```python
    "Holy Power": (
        EffectRule("crit_damage_pct", r"critical strike healing bonus of your Holy spells by (\d+(?:\.\d+)?)%",
                   ("Holy Light", "Flash of Light", "Holy Shock")),
    ),
```

## Step 9: `src/wowforever/classes/paladin.py`
Replace
```python
                   ("@instant",), sign=-1),
    ),
    "Twist of Light": (
        EffectRule("mana_cost_pct", r"Mana cost of your Seal spells by (\d+(?:\.\d+)?)%", ("@seal",), sign=-1),
    ),
```
with
```python
                   ("@instant",), sign=-1),
    ),
```

## Step 10: `src/wowforever/classes/paladin.py`
Replace
```python
    "Unyielding Faith": "defensive: shorter Fear and Disorient",
    "Voice of Truth": "defensive: immune to Silence and Interrupt for 6 s",
    "Purifying Power": "resource: cheaper Cleanse, shorter Exorcism/Holy Wrath cooldowns; neither is cast (#399)",
```
with
```python
    "Unyielding Faith": "defensive: shorter Fear and Disorient",
    "Oath of Light": "grants_spell",
    "Boundless Light": "healing: Holy Shock crit chance on allies without Oath of Light",
    "Purifying Power": "resource: cheaper Cleanse, shorter Exorcism/Holy Wrath cooldowns; neither is cast (#399)",
```

## Step 11: `src/wowforever/classes/paladin.py`
Replace
```python
    "Anticipation": "defensive: +20 Defense",
    "Improved Seal of Fury": "resource: mana when Seal of Fury's shield breaks",
    "Improved Righteous Fury": "defensive: 6% less damage taken in Righteous Fury",
```
with
```python
    "Anticipation": "defensive: +20 Defense",
    "Stoicism": "defensive: shorter Stun and Charm effects",
    "Shieldsworn": "threat: shorter Holy Strike cooldown, shield-based Holy Strike and spell blocks",
    "Improved Righteous Fury": "defensive: 6% less damage taken in Righteous Fury",
```

## Step 12: `src/wowforever/classes/paladin.py`
Replace
```python
    "Swift Judgement": "grants_spell",
    "One-Handed Weapon Specialization": "damage: +10% one-handed damage; Retribution swings a two-hander (#399)",
    "Improved Hammer of Justice": "control: Hammer of Justice cooldown -15 s",
```
with
```python
    "Swift Judgement": "grants_spell",
    "Improved Hammer of Justice": "control: Hammer of Justice cooldown -15 s",
```

## Step 13: `src/wowforever/classes/paladin.py`
Replace
```python
    "Repentance": "grants_spell",
    "Instrument of Law": "damage: faster Hammer of Wrath cast, less threat; its cast time isn't charged (#399)",
}
```
with
```python
    "Repentance": "grants_spell",
    "Turn Evil": "control: faster, shorter-cooldown Turn Undead that also affects Demons",
    "Unsealed Wrath": "proc: stores Seal copies for a second Seal's procs; the rotation keeps one Seal (#399)",
}
```

## Step 14: `config/group_buffs.toml`
Replace
```toml
spell_id = 24932
aura = 52           # melee and ranged crit since 1.60.1.70425 (was 290, all crit; #359)
provider = { class = "druid", talent = "Leader of the Pack", tree = "Feral Combat" }
```
with
```toml
spell_id = 24932
aura = 290          # all crit again since 1.60.1.70755 (52, melee and ranged, on 70425-70707; #359, #463)
provider = { class = "druid", talent = "Leader of the Pack", tree = "Feral Combat" }
```

## Step 15: `config/group_buffs.toml`
Replace
```toml
provider = { class = "druid", talent = "Leader of the Pack", tree = "Feral Combat" }
stack = "leader_of_the_pack"
reach = "physical"

```
with
```toml
provider = { class = "druid", talent = "Leader of the Pack", tree = "Feral Combat" }
stack = "druid_form_crit"     # exclusive with Moonkin Aura since 70755 (#463)
reach = "party"

```

## Step 16: `config/group_buffs.toml`
Replace
```toml
spell = "Moonkin Aura"
aura = 57           # spell crit since 1.60.1.70425 (was 290, all crit; #359)
provider = { class = "druid", talent = "Moonkin Form", tree = "Balance" }
```
with
```toml
spell = "Moonkin Aura"
aura = 290          # all crit again since 1.60.1.70755 (57, spell, on 70425-70707; #359, #463)
provider = { class = "druid", talent = "Moonkin Form", tree = "Balance" }
```

## Step 17: `config/group_buffs.toml`
Replace
```toml
provider = { class = "druid", talent = "Moonkin Form", tree = "Balance" }
stack = "moonkin_aura"
reach = "casters"

```
with
```toml
provider = { class = "druid", talent = "Moonkin Form", tree = "Balance" }
stack = "druid_form_crit"     # exclusive with Leader of the Pack since 70755 (#463)
reach = "party"

```
