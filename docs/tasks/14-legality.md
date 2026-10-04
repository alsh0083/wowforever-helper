# Task #14: build legality checker

Implement `src/wowforever/rules.py` so `tests/test_rules.py` passes. Do not edit the tests.

Reads everything from `wowforever.schema` (`ClassData`, `Talent`, `Rules`, `Prerequisite`): nothing class-specific.

## Interface
- `points_available(level: int, rules: Rules) -> int`: `level - first_talent_level + 1`, clamped to `[0, max_level - first_talent_level + 1]`
- `check_build(cls: ClassData, build: Mapping[int, int], level: int | None) -> list[str]`: `build` maps talent id → rank. Returns error messages; empty means legal. When `level` is None, skip only the point-budget check. Order-independent checks for a finished build:
  - unknown talent id (message names the id); rank < 1; rank > max rank (message names the talent and contains "max")
  - row gate: a talent in row r needs at least `r * points_per_row` points in rows `< r` of the **same tree** (message names the talent and the required number)
  - prerequisite talent must have at least the required rank (message names both talents)
  - total points ≤ `points_available(level)` (message contains the total and the available number)
- `check_order(cls: ClassData, order: Sequence[int]) -> list[str]`: one talent id per point; point i (1-based) is spent at level `first_talent_level + i - 1`. Simulate in order. Each bad point produces exactly one message starting `point {i} (level {L}):`, is **not applied**, and the simulation continues. Checks per point, in this order: past max level (message contains `max level {max_level}`), unknown id, already at max rank, prerequisite rank currently met, row gate against points currently spent. (The model swapped the last two: the prerequisite test can only fail on the prerequisite if it is checked first.)

Messages use talent names, not ids, except for unknown ids. Standard library only, type hints, short docstrings.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
