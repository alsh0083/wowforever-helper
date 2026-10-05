"""Exhaustive, lazy enumeration of legal talent builds.

Depth-first over the talents of the chosen trees, ordered by (tree, row, col).
A row gate is decided the moment its row starts (earlier rows are final), a
prerequisite is checked when its talent is chosen (already decided), and
branches are cut by the point budget and by what the remaining talents can
still contribute, so no finished build needs re-checking.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from .schema import ClassData, Talent


def enumerate_builds(
    cls: ClassData,
    *,
    budget: int,
    trees: Sequence[int],
    required: Sequence[int] = (),
) -> Iterator[dict[int, int]]:
    """Yield every legal build spending exactly `budget` points over `trees`.

    Builds map talent id to rank (ranks > 0 only). Every taken talent is at
    max rank except at most one partial, every `required` talent is at max
    rank, and per-tree row gates and prerequisites hold. Each build is
    yielded exactly once; the result is a lazy generator.
    """
    tree_set = set(trees)
    required_set = frozenset(required)
    ppr = cls.rules.points_per_row
    order = sorted(
        (t for t in cls.talents if t.tree_id in tree_set),
        key=lambda t: (t.tree_id, t.row, t.col),
    )
    n = len(order)
    suffix = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix[i] = suffix[i + 1] + order[i].max_rank
    # A row starts here: the earlier rows of its tree are final, so the gate
    # for this row (and every later row) is decided.
    starts_row = [
        i == 0
        or order[i].tree_id != order[i - 1].tree_id
        or order[i].row != order[i - 1].row
        for i in range(n)
    ]

    tree_remaining: dict[int, int] = {}
    for t in order:
        tree_remaining[t.tree_id] = tree_remaining.get(t.tree_id, 0) + t.max_rank

    build: dict[int, int] = {}
    tree_spent: dict[int, int] = {}
    locked: set[int] = set()

    def dfs(
        i: int, spent: int, partial_chosen: bool, locked_remaining: int
    ) -> Iterator[dict[int, int]]:
        """Walk order[i:]; `locked_remaining` is the unspent max of locked trees."""
        if i == n:
            if spent == budget:
                yield dict(build)
            return
        talent = order[i]
        tree = talent.tree_id
        max_rank = talent.max_rank
        locked_here = False
        if starts_row[i] and tree not in locked:
            if tree_spent.get(tree, 0) < talent.row * ppr:
                locked.add(tree)
                locked_remaining += tree_remaining[tree]
                locked_here = True
        try:
            pre = talent.prerequisite
            pre_ok = pre is None or build.get(pre.talent_id, 0) >= pre.rank
            is_required = talent.talent_id in required_set
            if tree in locked or not pre_ok:
                # The talent cannot be taken here; only skipping survives, and
                # a required talent may never be skipped.
                if is_required:
                    return
                choices = [0]
            else:
                choices = [] if is_required else [0]
                choices.append(max_rank)
                if not is_required and not partial_chosen and max_rank > 1:
                    choices.extend(range(1, max_rank))
            for c in choices:
                new_spent = spent + c
                if new_spent > budget:
                    continue
                tree_remaining[tree] -= max_rank
                child_locked = (
                    locked_remaining - max_rank if tree in locked else locked_remaining
                )
                if new_spent + suffix[i + 1] - child_locked < budget:
                    tree_remaining[tree] += max_rank
                    continue
                if c:
                    build[talent.talent_id] = c
                    tree_spent[tree] = tree_spent.get(tree, 0) + c
                yield from dfs(
                    i + 1, new_spent, partial_chosen or 0 < c < max_rank, child_locked
                )
                if c:
                    del build[talent.talent_id]
                    tree_spent[tree] -= c
                tree_remaining[tree] += max_rank
        finally:
            if locked_here:
                locked.discard(tree)

    yield from dfs(0, 0, False, 0)
