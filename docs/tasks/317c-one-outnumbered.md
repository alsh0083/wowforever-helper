# Task #317, part C: one outnumbered (2v1) path

Make `tests/test_one_outnumbered.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Before you start, `tests/test_one_outnumbered.py` fails at import (`best_outnumbered` doesn't exist). `tests/test_outnumbered.py` already uses it.
- Read only the files and functions named below. Don't re-check things this spec states.

## Why
The mage's report row takes the 2v1 score of its best filler's side; the other classes call
`class_pvp.outnumbered_score`. Both become one function over the engine's duel sides.

## Steps, in this order

### 1. `src/wowforever/pvp/duel.py`
At the end of the file add
`def best_outnumbered(sides, kits: Sequence[Kit]) -> tuple[float, str | None]:`.
`sides` is a list of `(name, Side)` pairs, as `ClassEngine.sides` returns them. Return
`(outnumbered_scores(side, kits)["score"], name)` for the side with the highest score; on a tie,
the earlier side. With no sides return `(0.5, None)`. Write a short docstring (#278, #317).

### 2. `src/wowforever/report.py`
- Import `best_outnumbered` from `wowforever.pvp.duel` and drop `outnumbered_scores` from that import.
- The mage's row (in `score_build`, the line `two = max(((outnumbered_scores(side, kits)["score"], spell) ...`):
  `two = best_outnumbered(sides, kits)`. The row it writes stays the same.
- `melee_report`: remove the local `from wowforever.pvp.class_pvp import outnumbered_score`. Where it
  computes `two = outnumbered_score(...)`, compute `two, _ = best_outnumbered(sides, kits)` instead.
  It needs `sides`, so move that line after `sides = engine(class_name).sides(...)`. The row it
  writes stays the same (no `spell` key for these classes).

### 3. `src/wowforever/pvp/class_pvp.py`
Delete `outnumbered_score` (the last function) and drop the imports nothing uses any more
(`Kit`, `outnumbered_scores`).

## Done when
- `tests/test_one_outnumbered.py` passes: 4 tests.
- The fast suite passes.
