# Task #337: immunity and pushback protection for non-mage duel sides

Make `tests/test_side_immunity_pushback.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation. The tests have the
expected values, and the steps below say what goes where.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. The package and dataset are ready; `latest_dataset_path()` is build 1.60.1.70374.
- Before you start, the 11 tests in the new file that need your change fail and the other 11 pass. Nothing else in the fast suite should fail.
- Read only the files named below. Don't re-check things this spec states.

## Why
A non-mage duel side (`class_side` in `src/wowforever/pvp/class_pvp.py`) always sets
`immunity_share=0.0` and never sets `pushback`, so paladins get no credit for Divine Shield and
casters none for their pushback talents. The mage gets both (`calc/pvp_axes.survival`).

## Steps, in this order

### 1. Tag four pushback talents (class modules)
Each talent below is currently a line in its module's `UNMODELED` dict. Remove that line and add
an entry to the same module's `TALENT_EFFECTS` dict: one `EffectRule("pushback_pct", <regex>, <applies_to>)`.
The regex has one capture group for the number. Copy the style of the mage's Burning Soul rule
(`src/wowforever/classes/mage.py`, search `pushback_pct`).

| Module | Talent | Rank text (rank 1) | applies_to |
|---|---|---|---|
| `classes/priest.py` | Twilight Focus | "Gives you a 23% chance to avoid interruption caused by damage while casting any spell." | `("all",)` |
| `classes/druid.py` | Nature's Focus | "Gives you a 14% chance to avoid interruption caused by damage while casting Arcane and Nature spells." | `("arcane", "nature")` |
| `classes/shaman.py` | Eye of the Storm | "Reduces the pushback suffered from damaging attacks while casting Lightning Bolt, Chain Lightning, and Lava Burst by 23%." | `("Lightning Bolt", "Chain Lightning", "Lava Burst")` |
| `classes/warlock.py` | Intensity | "Gives you a 23% chance to resist interruption caused by damage while casting or channeling any Destruction spell." | `("destruction",)` |

### 2. Config lists (`config/pvp_self.toml`)
- In the `[paladin]` table add `immunities = ["Divine Shield", "Divine Protection"]`, with a comment
  line above it: self-immunities for the survival axis and duels (#337); they share Forbearance, so the side takes the best one.
- Add `pushback_talents = ["<talent>"]` to `[priest]`, `[druid]`, `[shaman]` and `[warlock]` with the
  talent from step 1, with a comment line: talents that protect the class's damage casts from pushback (#337).
  Put both next to the existing `escapes = [...]` line where the table has one.

### 3. `class_side` (`src/wowforever/pvp/class_pvp.py`)
In the `Side(...)` call:
- `immunity_share`: instead of `0.0`, the largest `spell.immunity / spell.cooldown` over the names in
  `cfg.get("immunities", ())`, using `best_rank(spells, name, stats.level)`. Skip a spell that isn't
  learned yet (`None`) or has no cooldown. `0.0` when there are none.
- `pushback=`: the sum, over the talents named in `cfg.get("pushback_talents", ())` that are taken
  (`ranks.get(talent_id, 0) > 0`), of the `pushback_pct` effect value at the taken rank / 100, capped at 1.0.
  `cls.talent_named(name)` gives the talent; `effect.values[rank - 1]` is the value at a rank (the same
  pattern as `extra` and `tougher` a few lines above).

Then update the module docstring's "Not modeled yet" line if it names something you just modeled.

## Done when
- `tests/test_side_immunity_pushback.py` passes: 22 tests.
- The fast suite passes.
