# Task #358 (+ part of #359): warlock, druid and hunter talents on build 1.60.1.70425

Make `tests/test_70425_small_classes.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing; the package and dataset are ready.
- The model reads build 1.60.1.70425 (`config/dataset.toml`). Before you start, the new test file fails 7 tests.
  The fast suite has about 36 other failures for priest and shaman; they belong to other tasks.
  Leave them alone, and don't let your change add any new failure.
- Read only the files and functions named below. Don't re-check things this spec states.

## Why
Patch 1.60.1.70425 changed these talents' rank text (`TALENT_EFFECTS` rules read their numbers from it):
- Warlock **Malediction** became **Grim Reach**: 2 ranks, "Increases the range of your Affliction spells by
  10%/20%". The periodic damage bonus is gone. `config/talent_renames.toml` already maps the old name to the new.
- Warlock **Shadow Mastery**: 2% per rank, up to 10%. The existing rule may already read it; the test checks.
- Druid **Leader of the Pack**: "...increases the melee and ranged Critical Strike chance of all party or raid
  members within 45 yards by 3%."
- Hunter **Predator's Edge**: "Increases your melee ability critical strike damage by 6% and your Off Hand
  weapon damage by 10%" per rank. The crit bonus is for melee abilities now, not white swings.

## Steps, in this order

### 1. `src/wowforever/classes/warlock.py`
- Delete the `"Malediction"` entry from `TALENT_EFFECTS`.
- Add `"Grim Reach": "utility: range of Affliction spells (1.60.1.70425)"` to `UNMODELED`, in its Affliction part.

### 2. `src/wowforever/classes/druid.py`
In the `"Leader of the Pack"` rule, change the pattern so it matches the new text above (the number after
"within 45 yards by"). Keep the kind and `("@feral",)`.

### 3. `src/wowforever/classes/hunter.py` and `src/wowforever/classes/hunter_rotation.py`
- `hunter.py`, `"Predator's Edge"`: the crit rule's pattern matches "melee ability critical strike damage by",
  and its `applies_to` becomes `("@ability",)`. The off-hand rule stays.
- `hunter_rotation.py`, the petless melee block: `cd_m` stays the white swings' crit damage bonus. Add
  `cd_a = cd_m + total("crit_damage_pct", "@ability")` after it, and pass `crit_damage_pct=cd_a` (not `cd_m`)
  to the two `yellow_attack` calls (Raptor Strike, and Mongoose Bite / Strider Kick). The `white_swing` calls
  keep `cd_m`.

## Done when
- `tests/test_70425_small_classes.py` passes: 7 tests.
- The fast suite has no failures that weren't there before (check the warlock, druid and hunter ones are gone).
