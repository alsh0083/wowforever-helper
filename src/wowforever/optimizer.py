"""Point-order optimizer: greedy point selection with unlock look-ahead and deadline feasibility.

`optimize_order` turns a legal finished build into one talent id per point, the first point
at `rules.first_talent_level`. Each point starts the best *path*: for every talent still to take,
the shortest run of legal points that unlocks and takes it, scored by value gained per point. A
talent that is legal now is a one-point path, so this is plain greedy unless spending a few points
to unlock something (Mind Flay, a tree's 31-point talent) pays more per point. Candidates that
would leave a `must_have_by` deadline unreachable are dropped. Class-agnostic: all rules come from
the schema and `wowforever.rules`.
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
    memo: dict[tuple, float] = {}

    def cached(r: Mapping[int, int], level: int) -> float:
        key = (level, tuple(sorted((k, v) for k, v in r.items() if v)))
        if key not in memo:
            memo[key] = value(dict(r), level)
        return memo[key]

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
        allowed = {talent.talent_id for talent in survivors}
        now = cached(ranks, level)
        options = []
        for target in by_id.values():
            if target.talent_id not in ranks or ranks[target.talent_id] >= final[target.talent_id]:
                continue
            path = _unlock_path(target, ranks, final, by_id, cls.rules, lambda r: cached(r, level))
            if not path or path[0] not in allowed:
                continue
            after = dict(ranks)
            for tid in path:
                after[tid] += 1
            first = by_id[path[0]]
            options.append(((cached(after, level) - now) / len(path), len(path), first))
        if options:
            best = min(options, key=lambda o: (-o[0], o[1], o[2].row, o[2].col, o[2].talent_id))[2]
        else:   # every path starts outside the deadline-safe set: fall back to one point
            best = min(survivors, key=lambda t: (-cached({**ranks, t.talent_id: ranks[t.talent_id] + 1}, level),
                                                 t.row, t.col, t.talent_id))
        ranks[best.talent_id] += 1
        order.append(best.talent_id)
    return order


def _unlock_path(target: Talent, ranks: Mapping[int, int], final: Mapping[int, int],
                 by_id: Mapping[int, Talent], rules: Rules, score: Callable[[dict[int, int]], float],
                 limit: int = 15) -> list[int]:
    """The points that unlock and take one rank of `target`: while it is locked, the best-scoring legal
    point from the build that moves toward it (its prerequisite, or a point in a row above it in its
    tree). Empty if it can't be reached within `limit` points."""
    trial, path = dict(ranks), []
    while len(path) < limit:
        if _legal_now(target, trial, by_id, rules):
            return path + [target.talent_id]
        pre = target.prerequisite
        steps = [by_id[tid] for tid in trial
                 if trial[tid] < final[tid] and tid != target.talent_id and _legal_now(by_id[tid], trial, by_id, rules)
                 and ((pre is not None and tid == pre.talent_id and trial[tid] < pre.rank)
                      or (by_id[tid].tree_id == target.tree_id and by_id[tid].row < target.row))]
        if not steps:
            return []
        step = max(steps, key=lambda t: (score({**trial, t.talent_id: trial[t.talent_id] + 1}), -t.row, -t.col, -t.talent_id))
        trial[step.talent_id] += 1
        path.append(step.talent_id)
    return []


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


def optimize_free_order(
    cls: ClassData,
    value: Callable[[dict[int, int], int], float],
    *,
    main_tree: int,
    max_off_tree: int,
    total: int,
    early_off_tree: int | None = None,
    early_points: int = 0,
) -> list[int]:
    """A leveling path not tied to a finished build (owner request, 2026-10-07): `total` points, each on
    the best legal path's first point by `value` (as `optimize_order`), choosing from every talent of
    the class. At most `max_off_tree` points go outside `main_tree`, and at most `early_off_tree` within
    the first `early_points` (a small early dip, then deep), so the build stays in that tree's direction. Ties go to the main tree, then deeper rows, so points that don't change the score still
    head toward the tree's deep talents."""
    by_id = {t.talent_id: t for t in cls.talents}
    final = {t.talent_id: t.max_rank for t in cls.talents}
    ranks = {tid: 0 for tid in final}
    memo: dict[tuple, float] = {}

    def cached(r: Mapping[int, int], level: int) -> float:
        key = (level, tuple(sorted((k, v) for k, v in r.items() if v)))
        if key not in memo:
            memo[key] = value(dict(r), level)
        return memo[key]

    order: list[int] = []
    for index in range(1, total + 1):
        level = cls.rules.first_talent_level + index - 1
        off = sum(n for tid, n in ranks.items() if by_id[tid].tree_id != main_tree)
        cap = max_off_tree if early_off_tree is None or index > early_points else min(max_off_tree, early_off_tree)
        allowed = {t.talent_id for t in cls.talents
                   if ranks[t.talent_id] < t.max_rank and _legal_now(t, ranks, by_id, cls.rules)
                   and (t.tree_id == main_tree or off < cap)}
        if not allowed:
            raise ValueError(f"no legal point left at level {level}")
        now = cached(ranks, level)
        options = []
        for target in by_id.values():
            if ranks[target.talent_id] >= target.max_rank:
                continue
            path = _unlock_path(target, ranks, final, by_id, cls.rules, lambda r: cached(r, level))
            if not path or path[0] not in allowed:
                continue
            if sum(1 for tid in path if by_id[tid].tree_id != main_tree) + off > cap:
                continue
            after = dict(ranks)
            for tid in path:
                after[tid] += 1
            first = by_id[path[0]]
            rate = (cached(after, level) - now) / len(path)
            options.append((round(rate, 9), first.tree_id == main_tree, target.row, -len(path), -first.row,
                            -first.col, -first.talent_id, first))
        if options:
            best = max(options, key=lambda o: o[:7])[7]
        else:
            best = min((by_id[tid] for tid in allowed), key=lambda t: (t.tree_id != main_tree, t.row, t.col, t.talent_id))
        ranks[best.talent_id] += 1
        order.append(best.talent_id)
    return order
