"""Point-order optimizer: greedy point selection with deadline feasibility.

`optimize_order` turns a legal finished build into one talent id per point, the first point
at `rules.first_talent_level`. Each point takes the legal candidate with the best `value`,
dropping candidates that would leave a `must_have_by` deadline unreachable. Class-agnostic:
all rules come from the schema and `wowforever.rules`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from .rules import check_build
from .schema import ClassData, Rules, Talent


def optimize_order(
    cls: ClassData,
    final: Mapping[int, int],
    must_have_by: Mapping[int, int],
    value: Callable[[dict[int, int], int], float],
) -> list[int]:
    """Spend exactly `final`, one point per level, greedily on `value`.

    `must_have_by` maps talent id to the level by which it must reach its final rank;
    a candidate point that would make such a deadline infeasible is dropped.
    Raises ValueError if `final` is illegal or no candidate point remains.
    """
    problems = check_build(cls, final, level=None)
    if problems:
        raise ValueError("illegal final build:\n" + "\n".join(problems))
    by_id = {t.talent_id: t for t in cls.talents}
    ranks = {talent_id: 0 for talent_id in final}
    total = sum(final.values())
    order: list[int] = []
    for index in range(1, total + 1):
        level = cls.rules.first_talent_level + index - 1
        candidates = [
            by_id[talent_id]
            for talent_id in ranks
            if ranks[talent_id] < final[talent_id]
            and _legal_now(by_id[talent_id], ranks, by_id, cls.rules)
        ]
        survivors = [
            talent
            for talent in candidates
            if _keeps_deadlines_feasible(talent, ranks, final, must_have_by, by_id, cls.rules, level)
        ]
        if not survivors:
            raise _stuck(ranks, final, must_have_by, by_id, cls.rules, level)
        scored = [
            (-value({**ranks, talent.talent_id: ranks[talent.talent_id] + 1}, level), talent)
            for talent in survivors
        ]
        best = min(scored, key=lambda pair: (pair[0], pair[1].row, pair[1].col, pair[1].talent_id))[1]
        ranks[best.talent_id] += 1
        order.append(best.talent_id)
    return order


def _legal_now(talent: Talent, ranks: Mapping[int, int], by_id: Mapping[int, Talent], rules: Rules) -> bool:
    """True if the next point on `talent` is legal given the current `ranks`."""
    pre = talent.prerequisite
    if pre is not None and ranks.get(pre.talent_id, 0) < pre.rank:
        return False
    return _earlier_rows(talent, ranks, by_id) >= talent.row * rules.points_per_row


def _earlier_rows(talent: Talent, ranks: Mapping[int, int], by_id: Mapping[int, Talent]) -> int:
    """Points currently spent in rows above `talent`'s row, in its tree."""
    return sum(
        n
        for tid, n in ranks.items()
        if by_id[tid].tree_id == talent.tree_id and by_id[tid].row < talent.row
    )


def _keeps_deadlines_feasible(
    talent: Talent,
    ranks: Mapping[int, int],
    final: Mapping[int, int],
    must_have_by: Mapping[int, int],
    by_id: Mapping[int, Talent],
    rules: Rules,
    level: int,
) -> bool:
    """True if a point on `talent` leaves every pending deadline reachable."""
    after = {**ranks, talent.talent_id: ranks[talent.talent_id] + 1}
    for talent_id, deadline in must_have_by.items():
        if after.get(talent_id, 0) >= final.get(talent_id, 0):
            continue
        if _need(talent_id, after, final, by_id, rules) > deadline - level:
            return False
    return True


def _need(
    talent_id: int,
    ranks: Mapping[int, int],
    final: Mapping[int, int],
    by_id: Mapping[int, Talent],
    rules: Rules,
) -> int:
    """Lower bound on points still required before `talent_id` reaches its final rank."""
    talent = by_id[talent_id]
    pre = talent.prerequisite
    pre_missing = max(0, pre.rank - ranks.get(pre.talent_id, 0)) if pre is not None else 0
    gate_short = max(0, talent.row * rules.points_per_row - _earlier_rows(talent, ranks, by_id))
    return final.get(talent_id, 0) - ranks.get(talent_id, 0) + max(pre_missing, gate_short)


def _stuck(
    ranks: Mapping[int, int],
    final: Mapping[int, int],
    must_have_by: Mapping[int, int],
    by_id: Mapping[int, Talent],
    rules: Rules,
    level: int,
) -> ValueError:
    """Error for a state with no candidate point left."""
    pending = [
        (talent_id, deadline)
        for talent_id, deadline in must_have_by.items()
        if ranks.get(talent_id, 0) < final.get(talent_id, 0)
    ]
    if not pending:
        return ValueError(f"no legal point at level {level}")
    deficit = lambda pair: _need(pair[0], ranks, final, by_id, rules) - (pair[1] - level)
    worst_id, worst_deadline = min(pending, key=lambda pair: (-deficit(pair), pair[1], pair[0]))
    return ValueError(
        f"cannot meet deadline for {by_id[worst_id].name} (id {worst_id}) at level {worst_deadline}"
    )
