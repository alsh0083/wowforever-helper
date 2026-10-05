# Task #15: build enumerator

Implement `src/wowforever/enumerate.py` so `tests/test_enumerate.py` passes. Do not edit tests. Standard library only, type hints, short docstrings. Uses `wowforever.schema`; `wowforever.rules.check_build` is the reference for legality (you may call it, but a final check per build is too slow for real classes; prune while searching instead).

## Interface
`enumerate_builds(cls: ClassData, *, budget: int, trees: Sequence[int], required: Sequence[int] = ()) -> Iterator[dict[int, int]]`

Yields every build (talent id → rank, only ranks > 0) that:
- uses only talents in `trees`;
- spends exactly `budget` points;
- has every talent at **max rank except at most one** (the partial talent lets the budget come out exact);
- has every `required` talent at max rank;
- is legal: per-tree row gates (`row * points_per_row` points in earlier rows of the same tree) and prerequisites at their required rank.

Each build exactly once. It must be a **generator** (lazy): callers take the first N with `itertools.islice`.

## Approach (suggested)
Depth-first over talents sorted by (tree, row, col). For each talent choose: skip, full rank, or (if no partial chosen yet) each partial rank. Prune when points exceed the budget, when the points still available from the remaining talents can't reach it, or when a row's gate can no longer be met given what's been chosen in earlier rows (talents are visited row by row, so the earlier rows are final when a row starts). Check prerequisites when choosing a talent (its prerequisite is in an earlier row, so already decided). Required talents can't be skipped.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
