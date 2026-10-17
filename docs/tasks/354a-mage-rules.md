# Task #354, part A: mage talent rules on build 1.60.1.70425

Make `tests/test_70425_mage.py` pass (all but `test_ice_lance_frozen_multiplier_reads_the_rank_text`, which is part B) without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing; the package and dataset are ready.
- The model reads build 1.60.1.70425 (`config/dataset.toml`). Many older tests still read a 1.60.1.70205 fixture
  whose rank texts are the old wording, so **every pattern you change must match both the old and the new text**
  (the steps say how). Before you start, `tests/test_70425_mage.py` fails, and so do a few fixture tests in
  `test_talent_effects.py`, `test_pvp_axes.py`, `test_update.py` and `test_rotation.py`. Your change fixes them.
- The fast suite has failures for other classes; they belong to other tasks. After your change, two mage pins in
  `tests/test_dungeon_mana.py` will fail. That's expected, because Claude re-derives them. Any other new failure is not.
- Edit only `config/assumptions.toml` and `src/wowforever/classes/mage.py`. Read only the files and functions named below. Don't re-check things this spec states.

## Why
Patch 1.60.1.70425 changed these mage talents. `TALENT_EFFECTS` rules read their numbers from the rank text
(`effects.py`: one value per rank, `sign * combine(match)` when a rule has `combine`, else `group(1)`).

| Talent | Old text (70205 fixture) | New text (70425) |
|---|---|---|
| Fire Power (3 ranks, was 5) | "Increases the damage done by your Fire spells by 10%." | "Increases the damage done by your Fire spells by 3% per your Fire effects on the target, up to a maximum increase of 12%. ..." |
| Improved Frostbolt | "Reduces the casting time of your Frostbolt spell by 0.5 sec." | "Reduces the casting time of your Frostbolt and Frost Blast spells by 0.5 sec." |
| Wake of Fire → **Improved Fire Blast** (2 ranks) | "Reduces the cooldown of your Fire Blast spell by 2 sec. Killing ..." | "Reduces the cooldown of your Fire Blast spell by 2 sec and increases its range by 15 yards." |
| Winter's Chill | crit for Frostbolt and Ice Lance | "...increases the damage done by your Cone of Cold spell to the target by 40%, stacking up to 5 times." |
| Ice Lance | "Deals 300% increased damage to Frozen targets." | "Deals 200% increased damage to Frozen targets." |
| Arcane Wrath | (none) | a new 1-point talent that teaches a spell |

`config/talent_renames.toml` already maps Wake of Fire to Improved Fire Blast, and `ClassData.talent_named`
accepts either name.

## Steps, in this order

### 1. `config/assumptions.toml`
Append one entry in the file's format (see the entries above it):
`[fire_power_effects]` with `value = 2`, `options = [1, 2, 3, 4]`. `why`: Fire Power (1.60.1.70425) adds its % once
per Fire effect on the target, up to a cap; a Fire mage's boss keeps Ignite and Fireball's DoT up, and
Pyroblast's DoT and Flamestrike only some of the time. `source = "Fire Power rank text, 1.60.1.70425; issue #354"`,
`tested = ""`, `talents = ["Fire Power"]`.

### 2. `src/wowforever/classes/mage.py`
- Import `Assumptions` from `wowforever.assumptions` with the other imports.
- Add a function `_fire_power(match) -> float` above `TALENT_EFFECTS`. When `match.group(2)` is `None` (old text),
  return `float(group(1))`. Otherwise return `min(float(group(1)) * Assumptions.load()["fire_power_effects"],
  float(group(2)))`. Give it a short docstring.
- `"Fire Power"`: the pattern is "damage done by your Fire spells by (N)%" followed by an **optional** non-capturing
  group " per your Fire effects on the target, up to a maximum increase of (M)%"; `combine=_fire_power`. Add a
  comment line above it (x% per Fire effect, capped; the count is an assumption, #354).
- `"Improved Frostbolt"`: the pattern matches both texts: "casting time of your Frostbolt" then an optional
  " and Frost Blast", then " spell" or " spells", then " by (N) sec". `applies_to` becomes
  `("Frostbolt", "Frost Blast")`.
- Rename the `"Wake of Fire"` key to `"Improved Fire Blast"` (the rule itself stays).
- Delete the `"Winter's Chill"` entry from `TALENT_EFFECTS`. In `UNMODELED` add
  `"Winter's Chill": "damage: Cone of Cold +40% per stack on the target (1.60.1.70425); stacks need repeated Frost hits on one target, not modeled"`
  and `"Arcane Wrath": "grants_spell"`.

## Done when
- `tests/test_70425_mage.py` passes except `test_ice_lance_frozen_multiplier_reads_the_rank_text` (part B).
- `tests/test_talent_effects.py`, `tests/test_pvp_axes.py` and `tests/test_update.py` pass.
- Make the edits first, then run those test files; don't run the whole fast suite more than once.
