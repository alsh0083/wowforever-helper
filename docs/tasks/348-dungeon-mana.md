# Task #348: every class's dungeon pull runs on its mana pool

Make `tests/test_dungeon_mana.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation. The tests have the
expected values, and the steps below say what goes where.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing; the package and dataset are ready.
- Before you start, `tests/test_dungeon_mana.py` fails at import (`dungeon_pull` doesn't exist), and
  `tests/test_class_engine.py::test_casters_run_the_caster_rotation[warlock]` fails (it already expects
  step 3). Nothing else in the fast suite fails.
- Read only the files and functions named below. Don't re-check things this spec states.
- Don't regenerate the reports under `data/`; Claude does that after review.

## Why
The owner decided (#317) that mana limits every class's dungeon pull, as it does in Classic. Today only
the mage's dungeon runs on its mana pool (a branch in `group.dungeon_dps` that calls `scenarios.raid`);
every other class gets its rotation's full DPS for the whole pull. After this task every class goes through
one function, `melee_scenarios.dungeon_pull`: full DPS while the pool lasts, then the rotation's
`fallback_dps`. Warriors and rogues have no mana drain, so their numbers don't move.

## Steps, in this order

### 1. `src/wowforever/melee_scenarios.py`
- Add `import dataclasses` to the imports.
- Add `def dungeon_pull(out: Output, mana: float, level: int) -> float:` right after `dungeon()`. It
  returns `raid_dps` of `out` with `mana_cooldown` set to `None` (use `dataclasses.replace`), `mana`, and
  `default_params("dungeon", level)`. Docstring: DPS over one dungeon pull (#348), a 60 s pull on the
  mana pool with no potions and no Evocation.
- `dungeon()`: keep the armor and target lines; return `dungeon_pull(output, stats.mana, stats.level)`
  where `output` is the engine Output it computes today (not `.dps`). Its docstring loses
  "mana isn't limiting" and says it runs on the build's mana pool (#348).

### 2. `src/wowforever/group.py`, `dungeon_dps`
- Delete the `if class_name == "mage":` block (it ends with `return r.score * magic_multiplier(eff)`).
  The mage then takes the same path as every other class.
- The line `out = engine(class_name).output(buffed, ...).dps` becomes
  `out = ms.dungeon_pull(engine(class_name).output(buffed, ...), buffed.mana, stats.level)`, with the
  same `output(...)` arguments as today. Nothing else in the function changes.

### 3. Warlocks tap once dry: `config/casters.toml` and `src/wowforever/classes/engines.py`
- `config/casters.toml`, `[warlock]`: on the line after `extra_regen_per_second = 15.0` add a two-line
  comment and one key. Values are Forever's Life Tap SpellEffect base points (wago 1.60.1.70291), per
  rank's level:
  ```
  # once dry, the warlock taps instead of waiting on regen (#348): one GCD per tap; mana per rank =
  # Forever SpellEffect base points + 1 per level above the rank's level (wago 1.60.1.70291)
  life_tap = { gcd = 1.5, ranks = [[6, 20], [16, 65], [26, 130], [36, 210], [46, 300], [56, 420]] }
  ```
- `engines.py`: add `def life_tap_fallback(dps: float, drain: float, level: int, tap) -> float:` before
  `caster_aoe`. With `drain <= 0` return `dps`. Otherwise take the highest rank whose level is `<= level`;
  its mana is the rank's value plus `level - rank level`. Return `dps / (1 + drain * tap["gcd"] / mana)`
  (the test file has worked values).
- `caster_output`: after `fallback` is computed, if `caster_config(class_name)` (import it from
  `wowforever.gear`) has a `"life_tap"` entry, set
  `fallback = life_tap_fallback(r.dps, r.mana_per_second, stats.level, that entry)`.

### 4. `src/wowforever/classes/mage.py`, `output`
The caster engine's `Output.mana_per_second` is net of in-combat regen; the mage's is gross. Make the
mage's net, too. At the end of `output` (the non-sustained path), `income = combat_regen(char,
default_params("raid", stats.level))` stays, but keep the params in a variable `p`. The returned
`Output`'s second argument becomes `rot.mana_per_second - (income - p.mana_per_second)` (the same net
drain `_raid_output` uses). `fallback` doesn't change.

## Done when
- `tests/test_dungeon_mana.py` passes: 12 tests.
- The fast suite passes.
