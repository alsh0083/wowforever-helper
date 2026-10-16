# Task #317, part A: the shared raid gets the mage's raid mechanics

Make `tests/test_shared_raid.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation. The tests have the
expected values, and the steps below say what goes where.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing; the package and dataset are ready.
- Before you start, `tests/test_shared_raid.py` fails at import (`raid_dps` doesn't exist). Nothing else in the fast suite fails.
- Read only the files and functions named below. Don't re-check things this spec states.

## Why
Every class's raid score should come from one function, `melee_scenarios.raid`. The mage still uses
its own `scenarios.raid`, because the shared one lacks three mage mechanics: rotations with long
cooldowns averaged in (`sustained=True`), Evocation's mana, and a fallback that tries every filler
rank once the mage is out of mana. Part A gives the shared raid those mechanics. The mage's raid
numbers must come out exactly as `scenarios.raid` gives them, and no other class's numbers may move.

## Steps, in this order

### 1. `src/wowforever/melee_scenarios.py`
- `Output`: add a last field `mana_cooldown: tuple[float, float] | None = None`, with a comment:
  (channel seconds, mana) a class spends to refill when a raid fight would run it dry (Evocation, #317).
- Move the fight-length loop out of `raid()` into a new function `raid_dps(out: Output, mana: float, p) -> float`
  (`p` is a `scenarios.RaidParams`). It works as the loop does today, with one addition. Per fight
  length, when `drain > 0` and `out.mana_cooldown` is set and `budget / drain < seconds`, add the
  cooldown's mana to the budget and subtract its channel seconds from the active time. Then
  `full = min(active, budget / drain)` and `score = (dps x full + fallback_dps x (active - full)) / seconds`.
  The test file's docstring has the hand-worked cases. Write a short docstring.
- `raid()`: call the engine's `output(...)` with `sustained=True` and return
  `raid_dps(out, stats.mana, default_params("raid", stats.level))`.

### 2. Every class's `output` accepts `sustained`
- In `src/wowforever/classes/__init__.py`, the `ClassEngine.output` protocol method gets a keyword
  `sustained: bool = False` after `melee`. Add a line to its docstring: `sustained` asks for a raid
  fight's rotation, with long-cooldown buffs averaged in (#317).
- Each of `classes/druid.py, hunter.py, paladin.py, priest.py, rogue.py, shaman.py, warlock.py, warrior.py`
  has `def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None):`.
  Add `, sustained=False` at the end of the parameters and change nothing else; those classes ignore it.

### 3. `src/wowforever/classes/mage.py`
`output` gets the same `sustained=False` parameter. When `sustained` is true, return the result of a
new module-level function `_raid_output(char, target_level, assumptions)`, called right after
`target_level` is computed. Put that function at the end of the file. It mirrors
`scenarios._raid_with` and `scenarios.raid` (read those two functions) without the per-length scoring:

- `p = default_params("raid", char.level)`; `income = combat_regen(char, p)`.
- Evocation as the mana cooldown when `p.evocation`:
  `(p.evocation_seconds, spirit_regen(char.stats) * (1 + p.evocation_regen_pct / 100) * p.evocation_seconds)`, else `None`.
- For each filler in `usable_fillers(char, p.fillers, target_level, assumptions)`:
  - `rot = rotation(char, filler, target_level=..., assumptions=..., sustained=True)`.
  - The fallback is `scenarios._fallback(char, p, filler, target_level, assumptions, income)[0]` when `p.fallback` and `rot.mana_per_second > income`, else `0.0`.
  - Build `Output(rot.dps, rot.mana_per_second - (income - p.mana_per_second), fallback, ranged=True, spell=filler.name, mana_cooldown=<evocation>)`. The mana is net of the mage's own regen while casting, as the other casters report it; `raid_dps` subtracts the raid's flat income itself.
  - Score it with `raid_dps(output, char.stats.mana, p)`.
- Return the Output with the best score (the first one on a tie). Raise `ValueError` when there's no filler.
- Import inside the function, as the rest of the module does: `rotation` from `wowforever.classes.mage_rotation`, `Output` and `raid_dps` from `wowforever.melee_scenarios`, and `_fallback`, `combat_regen`, `default_params`, `spirit_regen`, `usable_fillers` from `wowforever.scenarios`.

## Done when
- `tests/test_shared_raid.py` passes: 15 tests.
- The fast suite passes.
