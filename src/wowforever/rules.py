"""Build legality rules for a talent dataset.

`check_build` validates a finished build (talent id -> rank) order-independently;
`check_order` simulates a spending order one point at a time. Everything is read
from the schema types; nothing here is class-specific.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .schema import ClassData, Rules, Talent


def points_available(level: int, rules: Rules) -> int:
    """Talent points available at `level`, clamped to [0, max-level cap]."""
    points = level - rules.first_talent_level + 1
    return max(0, min(points, rules.max_level - rules.first_talent_level + 1))


def check_build(cls: ClassData, build: Mapping[int, int], level: int | None) -> list[str]:
    """Check a finished build; an empty list means legal.

    With `level` given the total point count is checked against the point
    budget as well; with `level=None` only that check is skipped.
    """
    by_id = {t.talent_id: t for t in cls.talents}
    errors: list[str] = []
    taken: list[tuple[Talent, int]] = []
    total = 0
    for talent_id, rank in build.items():
        talent = by_id.get(talent_id)
        if talent is None:
            errors.append(f"unknown talent {talent_id}")
            continue
        if rank < 1:
            errors.append(f"{talent.name}: rank {rank} is below the minimum of 1")
        elif rank > talent.max_rank:
            errors.append(f"{talent.name}: rank {rank} exceeds max rank {talent.max_rank}")
        taken.append((talent, _spendable_rank(talent, rank)))
        total += max(rank, 0)
    for talent, _ in taken:
        errors.extend(_structure_errors(talent, taken, by_id, cls.rules.points_per_row))
    if level is not None:
        available = points_available(level, cls.rules)
        if total > available:
            errors.append(f"total {total} points exceeds {available} available at level {level}")
    return errors


def check_order(cls: ClassData, order: Sequence[int]) -> list[str]:
    """Simulate spending `order` point by point; each bad point is skipped.

    Point i (1-based) is spent at level `first_talent_level + i - 1`. A bad
    point produces exactly one message, is not applied, and the simulation
    continues with the remaining points.
    """
    by_id = {t.talent_id: t for t in cls.talents}
    errors: list[str] = []
    ranks: dict[int, int] = {}
    for index, talent_id in enumerate(order, start=1):
        level = cls.rules.first_talent_level + index - 1
        prefix = f"point {index} (level {level}): "
        if level > cls.rules.max_level:
            errors.append(f"{prefix}level {level} is past max level {cls.rules.max_level}")
            continue
        talent = by_id.get(talent_id)
        if talent is None:
            errors.append(f"{prefix}unknown talent {talent_id}")
            continue
        rank = ranks.get(talent_id, 0)
        if rank >= talent.max_rank:
            errors.append(f"{prefix}{talent.name} is already at max rank {talent.max_rank}")
            continue
        pre = talent.prerequisite
        if pre is not None and ranks.get(pre.talent_id, 0) < pre.rank:
            errors.append(
                f"{prefix}{talent.name} requires {by_id[pre.talent_id].name} at rank {pre.rank}"
            )
            continue
        needed = talent.row * cls.rules.points_per_row
        earlier = sum(
            n
            for tid, n in ranks.items()
            if by_id[tid].tree_id == talent.tree_id and by_id[tid].row < talent.row
        )
        if earlier < needed:
            errors.append(
                f"{prefix}{talent.name} requires {needed} points in earlier rows of the same tree"
            )
            continue
        ranks[talent_id] = rank + 1
    return errors


def _spendable_rank(talent: Talent, rank: int) -> int:
    """Points `rank` contributes to tree totals, clamped to [0, max_rank]."""
    return max(0, min(rank, talent.max_rank))


def _structure_errors(
    talent: Talent,
    taken: list[tuple[Talent, int]],
    by_id: dict[int, Talent],
    points_per_row: int,
) -> list[str]:
    """Prerequisite and row-gate errors for one talent of a finished build."""
    errors: list[str] = []
    pre = talent.prerequisite
    if pre is not None:
        pre_rank = next((n for t, n in taken if t.talent_id == pre.talent_id), 0)
        if pre_rank < pre.rank:
            errors.append(f"{talent.name} requires {by_id[pre.talent_id].name} at rank {pre.rank}")
    needed = talent.row * points_per_row
    earlier = sum(n for t, n in taken if t.tree_id == talent.tree_id and t.row < talent.row)
    if earlier < needed:
        errors.append(f"{talent.name} requires {needed} points in earlier rows of the same tree")
    return errors
