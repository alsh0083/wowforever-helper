# Task #162 (part 1): warrior rage costs

Make `tests/test_rage_cost.py` pass without breaking the rest of the suite. Edit `src/wowforever/schema.py` and `src/wowforever/normalize_spells.py`. Do not edit the tests or fixtures.

## Why
Warrior abilities cost Rage. The client stores it in `SpellPower` rows with `PowerType` 1, in tenths (Mortal Strike's `ManaCost` is 300 = 30 Rage). Rogue energy (PowerType 3) is already parsed the same way into `energy_cost`.

## 1. `src/wowforever/schema.py`
In `SpellRank`, right after the `energy_cost` field, add:

    rage_cost: int = 0                 # warrior rage (SpellPower PowerType 1, stored in tenths, #162)

## 2. `src/wowforever/normalize_spells.py`
- Next to `_POWER_MANA, _POWER_ENERGY = "0", "3"`, add a constant `_POWER_RAGE = "1"`.
- Where `energy_cost = costs.get(_POWER_ENERGY, 0)` is computed, add `rage_cost = costs.get(_POWER_RAGE, 0) // 10`.
- Pass `rage_cost=rage_cost` to the `SpellRank(...)` call, next to `energy_cost=energy_cost`.

That is the whole change: three small edits.

## Environment note
The package is installed in `.venv` (editable). Before you start, `tests/test_rage_cost.py` fails because `rage_cost` doesn't exist. Install nothing and ask for no elevation. Make each edit with one `tools/apply_patch.py` call (see AGENTS.md); if an apply_patch call fails once, read the error, re-read the file and retry with the exact current text; don't write scratch files to debug it. Iterate with `.venv/Scripts/python -m pytest tests/test_rage_cost.py`.

## Done when
`.venv/Scripts/python -m pytest tests/test_rage_cost.py` passes.
