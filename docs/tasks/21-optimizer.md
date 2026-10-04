# Task #21: point-order optimizer

Implement `src/wowforever/optimizer.py` so `tests/test_optimizer.py` passes. Do not edit tests. Standard library only, type hints, short docstrings. Uses `wowforever.rules` (`check_build`) and `wowforever.schema`.

## Interface
`optimize_order(cls: ClassData, final: Mapping[int, int], must_have_by: Mapping[int, int], value: Callable[[dict[int, int], int], float]) -> list[int]`

- `final`: talent id → rank of the finished build; `must_have_by`: talent id → level by which that talent must reach its **final** rank; `value(ranks, level)`: value of a partial build (talent id → rank) at a level.
- Returns one talent id per point, first point at `cls.rules.first_talent_level`, spending exactly `final`.

## Algorithm (deterministic greedy with deadline feasibility)
1. If `check_build(cls, final, level=None)` reports problems, raise `ValueError` with them.
2. For point i = 1..total (level L = first_talent_level + i - 1): candidates = talents in `final` below their final rank whose next point is **legal now** (row gate counts points currently spent in earlier rows of the same tree; prerequisite rank currently met).
3. Drop candidates that make a pending deadline infeasible. A deadline (T, D) is feasible after a tentative point if `need(T) <= D - L`, where `need(T)` = a lower bound on points still required before T reaches its final rank: T's missing ranks + **max**(the prerequisite's missing ranks up to the required rank, `max(0, points_per_row * T.row - points in earlier rows of T's tree)`). It's a max, not a sum, because the prerequisite sits in an earlier row of the same tree, so its points also count toward T's row gate. Deadlines already met are not pending.
4. Among the remaining candidates pick the one maximizing `value(ranks_after_point, L)`; ties by (row, col, talent id) ascending.
5. If no candidate remains, raise `ValueError` naming the talent whose deadline can't be met (or "no legal point" if no deadlines are involved).

## Done when
`.venv/Scripts/python -m pytest` passes in full.
