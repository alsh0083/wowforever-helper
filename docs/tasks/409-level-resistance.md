# Task #409: level-based spell resistance (default on) and Arcane Subtlety

Make `tests/test_level_resistance.py` pass. Other tests that pin caster scores will move; Claude re-pins them.
Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit in this order: `config/assumptions.toml`, `src/wowforever/schema.py`,
  `src/wowforever/calc/ev.py`, `src/wowforever/calc/talents.py`, `src/wowforever/classes/mage.py`,
  `src/wowforever/caster.py`, `src/wowforever/classes/mage_rotation.py`, `src/wowforever/scenarios.py`.
- Run `tests/test_level_resistance.py` and `tests/test_ev_golden.py` (both must pass), then the fast suite once
  and just report which other tests fail (expected: caster and mage score pins). Do not try to fix those.
- Before you start, `tests/test_level_resistance.py` fails to import.

## Why
Owner decision (2026-10-19, #409): model level-based resistance, default on. Classic: a target above the caster's
level resists spells as if it had 8 resistance per level of difference; the average partial resist is
resistance / (caster level x 5) x 0.75. Arcane Subtlety lowers the resistance. Holy damage isn't resisted.

## Step 1: `config/assumptions.toml`
At the end of the file, add (one blank line before it):
```toml
[level_resistance]
value = true
options = [false, true]
why = "A target above the caster's level resists spells as if it had 8 resistance per level of difference: on average resistance / (caster level x 5) x 0.75 of the damage (-6% at 60 against a 63 boss). Holy damage isn't resisted; physical damage is untouched (owner decision 2026-10-19, #409)."
source = "Classic resistance mechanics (level-based resistance, average partial resist); not yet checked in Forever"
tested = ""
talents = ["Arcane Subtlety"]
```

## Step 2: `src/wowforever/schema.py`
In `EFFECT_KINDS`, after the `"direct_damage_pct",` line, add:
```python
    "resistance_reduction",  # resistance taken off the target for your spells (Arcane Subtlety)
```

## Step 3: `src/wowforever/calc/ev.py`
1. In the module docstring, replace `Resistances are ignored in v0.` with
   `Level-based resistance (#409) is an average partial resist, when the caller asks for it.`
2. In `class Modifiers`, after the `direct_damage_pct` field, add:
```python
    resistance_reduction: float = 0.0   # resistance taken off the target (Arcane Subtlety, #409)
```
3. Directly before `def expected_damage(`, add:
```python
def level_resist_pct(caster_level: int, target_level: int, reduction: float = 0.0) -> float:
    """Average % of spell damage a higher-level target resists (#409, Classic): 8 resistance per level above the
    caster, less `reduction`, resisted on average resistance / (caster level x 5) x 0.75."""
    resistance = max(0.0, 8.0 * (target_level - caster_level) - reduction)
    return resistance / (caster_level * 5.0) * 0.75 * 100.0


```
4. `expected_damage` gains a keyword-only parameter `level_resistance: bool = False` after
   `periodic_can_crit: bool = False,`. Its final line `    return direct + periodic + ignite` becomes:
```python
    total = direct + periodic + ignite
    if level_resistance and "holy" not in spell.schools:
        total *= 1.0 - level_resist_pct(caster_level, target_level, mods.resistance_reduction) / 100.0
    return total
```

## Step 4: `src/wowforever/calc/talents.py`
In `_KIND_TO_FIELD`, after the `"direct_damage_pct": "direct_damage_pct",` line, add:
```python
    "resistance_reduction": "resistance_reduction",
```

## Step 5: `src/wowforever/classes/mage.py`
1. At the end of `TALENT_EFFECTS` (directly before its closing `}`), add:
```python
    "Arcane Subtlety": (
        EffectRule("resistance_reduction", r"resistance to all your spells by (\d+(?:\.\d+)?)", ("all",)),
    ),
```
2. Delete the `UNMODELED` line `    "Arcane Subtlety": "resistance reduction + threat, v1",`.

## Step 6: the callers pass the assumption
In each of these `expected_damage(...)` calls, add the argument
`level_resistance=bool(assumptions["level_resistance"])` (each call already has an `assumptions` variable in scope):
- `src/wowforever/caster.py`, the call at `    ev = expected_damage(sub20_penalized(...`;
- `src/wowforever/classes/mage_rotation.py`, both calls (in `frozen_hit_gain`'s `ev_of` and in `rotation`'s `ev_of`);
- `src/wowforever/scenarios.py`, the call near line 153.
Put the new argument last, after `periodic_can_crit=...`, keeping lines under 120 characters (wrap as the
surrounding code does).

Nothing else changes.

## Done when
- `tests/test_level_resistance.py` and `tests/test_ev_golden.py` pass; report the other failures (score pins).
