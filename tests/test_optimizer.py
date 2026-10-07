"""Tests for the point-order optimizer (#21), on the synthetic class from test_rules.py.

Tree 1:  row 0: A1 (5), A2 (3); row 1: B1 (2); row 2: C1 (1, requires B1 2/2)
Tree 2:  row 0: X1 (5)
First point at level 10; 5 points per row.
"""

import pytest

from wowforever.optimizer import optimize_order
from wowforever.rules import check_order
from wowforever.schema import ClassData, Prerequisite, Rules, Talent, Tree

A1, A2, B1, C1, X1 = 1, 2, 3, 4, 5
CLS = ClassData(
    "testclass",
    (Tree(1, "One", (A1, A2, B1, C1)), Tree(2, "Two", (X1,))),
    (
        Talent(A1, "A1", 1, 0, 0, 5, (), ()),
        Talent(A2, "A2", 1, 0, 1, 3, (), ()),
        Talent(B1, "B1", 1, 1, 0, 2, (), ()),
        Talent(C1, "C1", 1, 2, 0, 1, (), (), Prerequisite(B1, 2)),
        Talent(X1, "X1", 2, 0, 0, 5, (), ()),
    ),
    rules=Rules(first_talent_level=10, max_level=60, points_per_row=5),
)


def weighted(weights):
    """Value of a partial build = sum of weight * rank (the level is ignored)."""
    return lambda ranks, level: sum(weights.get(t, 0) * r for t, r in ranks.items())


def test_greedy_takes_the_most_valuable_legal_point_each_level():
    final = {A1: 5, A2: 3, B1: 2, C1: 1}
    order = optimize_order(CLS, final, {}, weighted({C1: 100, B1: 10, A2: 2, A1: 1}))
    # A2 is worth more than A1 until it's maxed; B1 opens at 5 points; C1 needs 10 in rows 0-1
    assert order == [A2, A2, A2, A1, A1, B1, B1, A1, A1, A1, C1]
    assert check_order(CLS, order) == []


def test_ties_break_by_row_then_column_then_id():
    final = {A1: 1, A2: 1}
    assert optimize_order(CLS, final, {}, weighted({})) == [A1, A2]


def test_must_have_deadline_overrides_greedy_value():
    # X1 is worth the most, but C1 must be in by level 20 (point 11), which needs all 11 tree-1
    # points first; greedy alone would spend points 1-5 on X1 and get C1 at point 16 (level 25)
    final = {A1: 5, A2: 3, B1: 2, C1: 1, X1: 5}
    value = weighted({X1: 50, C1: 100, B1: 10, A2: 2, A1: 1})
    assert optimize_order(CLS, final, {}, value)[:5] == [X1] * 5
    order = optimize_order(CLS, final, {C1: 20}, value)
    assert order.index(C1) + 10 <= 20
    assert order[11:] == [X1] * 5
    assert check_order(CLS, order) == []


def test_order_spends_exactly_the_final_build():
    final = {A1: 5, A2: 3, B1: 2, C1: 1, X1: 3}
    order = optimize_order(CLS, final, {}, weighted({X1: 1}))
    assert sorted(order) == sorted(t for t, r in final.items() for _ in range(r))


def test_unreachable_deadline_raises():
    final = {A1: 5, A2: 3, B1: 2, C1: 1}
    with pytest.raises(ValueError, match="C1"):
        optimize_order(CLS, final, {C1: 15}, weighted({}))


def test_illegal_final_build_raises():
    with pytest.raises(ValueError):
        optimize_order(CLS, {C1: 1}, {}, weighted({}))


def test_value_function_sees_level_of_the_point_being_chosen():
    seen = []

    def value(ranks, level):
        seen.append(level)
        return 0

    optimize_order(CLS, {A1: 2}, {}, value)
    assert set(seen) == {10, 11}


def test_look_ahead_unlocks_a_deep_talent_worth_more_per_point_than_the_greedy_pick():
    # X1 pays 3 per point now; tree One's points pay almost nothing until C1 (worth 100) opens after
    # 10 of them: 100 / 11 points beats 3 per point, so the order heads down tree One first
    final = {A1: 5, A2: 3, B1: 2, C1: 1, X1: 5}
    order = optimize_order(CLS, final, {}, weighted({C1: 100, X1: 3, A1: 0.1, A2: 0.1, B1: 0.1}))
    assert order.index(C1) == 10 and order[11:] == [X1] * 5
    assert check_order(CLS, order) == []


def test_free_order_picks_talents_by_value_and_caps_off_tree_points():
    from wowforever.optimizer import optimize_free_order

    # tree One is the main tree; X1 (tree Two) pays most but only 2 off-tree points are allowed
    order = optimize_free_order(CLS, weighted({X1: 10, A2: 2, A1: 1, B1: 1, C1: 50}), main_tree=1, max_off_tree=2, total=8)
    assert order.count(X1) == 2 and order[:2] == [X1, X1]
    assert check_order(CLS, order) == []
