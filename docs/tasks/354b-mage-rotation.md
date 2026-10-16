# Task #354, part B: the mage rotation on build 1.60.1.70425

Make the rest of `tests/test_70425_mage.py` pass (part A, the rules in `mage.py`, is done) without breaking the rest of the fast suite
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
- Edit only `src/wowforever/classes/mage_rotation.py`. Read only the functions named below. Don't re-check things this spec states.

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

## Steps

### `src/wowforever/classes/mage_rotation.py`
- Add `def frozen_lance_multiplier(cls) -> float:` above `frozen_hit_gain`. It reads the Ice Lance talent's last
  rank text (`cls.talent_named("Ice Lance").rank_text[-1]`), finds "Deals (N)% increased damage to Frozen
  targets", and returns `1 + N / 100`. Docstring: 200% on 1.60.1.70425, so 3.0 (#354).
- `frozen_hit_gain` and `rotation` each build a frozen Ice Lance with `4.0` as the multiplier on
  `min_damage`, `max_damage` and `coefficient`. Use `frozen_lance_multiplier(char.cls)` instead in both places,
  and fix the `# +300% damage ...` comment so it doesn't name a number.
- `rotation`, inner function `value(name, kind)`: look the talent up with `char.cls.talent_named(name)`, which
  accepts renamed talents; on `KeyError` return 0.0. The rank is `char.ranks.get(talent.talent_id, 0)`. The rest
  stays the same.
- The Fire Blast weave line `value("Wake of Fire", "cooldown")` becomes `value("Improved Fire Blast", "cooldown")`,
  and its comment just says the value is negative.

## Done when
- `tests/test_70425_mage.py` (7 tests) and `tests/test_rotation.py` pass.
- Make the edits first, then run those two files; then the fast suite once. Only the two mage pins in
  `tests/test_dungeon_mana.py` may fail.
