"""Tests for the build legality checker (#14), on a small synthetic class.

Tree 1:  row 0: A1 (5 ranks), A2 (3 ranks)
         row 1: B1 (2 ranks)
         row 2: C1 (1 rank, requires B1 at rank 2)
Tree 2:  row 0: X1 (5 ranks)

Rules: first talent point at level 10, max level 60, 5 points per row (row r needs 5*r points
spent in that tree's earlier rows).
"""

import pytest

from wowforever.rules import check_build, check_order, points_available
from wowforever.schema import ClassData, Prerequisite, Rules, Talent, Tree

A1, A2, B1, C1, X1 = 1, 2, 3, 4, 5


def talent(tid, name, tree, row, col, max_rank, prereq=None):
    return Talent(tid, name, tree, row, col, max_rank, (), (), prereq)


CLS = ClassData(
    "testclass",
    (Tree(1, "One", (A1, A2, B1, C1)), Tree(2, "Two", (X1,))),
    (
        talent(A1, "A1", 1, 0, 0, 5),
        talent(A2, "A2", 1, 0, 1, 3),
        talent(B1, "B1", 1, 1, 0, 2),
        talent(C1, "C1", 1, 2, 0, 1, Prerequisite(B1, 2)),
        talent(X1, "X1", 2, 0, 0, 5),
    ),
    rules=Rules(first_talent_level=10, max_level=60, points_per_row=5),
)


@pytest.mark.parametrize("level, points", [(1, 0), (9, 0), (10, 1), (11, 2), (60, 51), (70, 51)])
def test_points_available(level, points):
    assert points_available(level, CLS.rules) == points


# ---- final builds ------------------------------------------------------------------------------

def test_legal_build():
    assert check_build(CLS, {A1: 5, A2: 3, B1: 2, C1: 1, X1: 2}, level=60) == []


def test_empty_build_is_legal():
    assert check_build(CLS, {}, level=10) == []


def test_row_gate_counts_only_earlier_rows_of_the_same_tree():
    # C1 (row 2) needs 10 points in rows 0-1 of tree 1; A1 5 + B1 2 = 7. X1 points don't count.
    errors = check_build(CLS, {A1: 5, B1: 2, C1: 1, X1: 5}, level=60)
    assert len(errors) == 1 and "C1" in errors[0] and "10" in errors[0]


def test_prerequisite_rank_must_be_met():
    errors = check_build(CLS, {A1: 5, A2: 3, B1: 1, C1: 1}, level=60)
    assert any("C1" in e and "B1" in e for e in errors)


def test_rank_above_max_and_unknown_talent():
    errors = check_build(CLS, {A1: 6, 99: 1}, level=60)
    assert any("A1" in e and "max" in e for e in errors)
    assert any("99" in e for e in errors)


def test_zero_or_negative_rank_rejected():
    assert check_build(CLS, {A1: 0}, level=60) != []


def test_too_many_points_for_level():
    # level 15 -> 6 points available
    errors = check_build(CLS, {A1: 5, A2: 2}, level=15)
    assert len(errors) == 1 and "7" in errors[0] and "6" in errors[0]


def test_level_none_skips_point_budget_only():
    assert check_build(CLS, {A1: 5, A2: 3, B1: 2, C1: 1, X1: 5}, level=None) == []


# ---- point orders (one talent id per point, first point at first_talent_level) ----------------

def test_legal_order():
    order = [A1] * 5 + [B1, B1, A2, A2, A2, C1]
    assert check_order(CLS, order) == []


def test_order_rejects_row_gate_at_the_point_it_happens():
    errors = check_order(CLS, [A1, B1])
    # point 2 (level 11): B1 is row 1, needs 5 points in row 0, only 1 spent
    assert len(errors) == 1 and "point 2" in errors[0] and "level 11" in errors[0]


def test_order_rejects_prerequisite_not_yet_met():
    order = [A1] * 5 + [A2] * 3 + [B1, C1, B1]
    errors = check_order(CLS, order)
    assert len(errors) == 1 and "point 10" in errors[0] and "B1" in errors[0]


def test_order_rejects_exceeding_max_rank():
    errors = check_order(CLS, [A2] * 4)
    assert len(errors) == 1 and "point 4" in errors[0]


def test_order_longer_than_max_level_allows():
    # 52 points: point 52 would be spent at level 61, past max level 60. Points 17-51 also fail
    # (every talent already maxed); only the last error is about the level cap.
    errors = check_order(CLS, [A1] * 5 + [A2] * 3 + [B1] * 2 + [C1] + [X1] * 5 + [A1] * 36)
    assert "point 52" in errors[-1] and "max level 60" in errors[-1]
    assert not any("max level" in e for e in errors[:-1])


def test_order_reports_every_bad_point_and_continues_without_applying_it():
    # bad B1 at point 1 is skipped; the following A1s are still legal
    errors = check_order(CLS, [B1, A1, A1])
    assert len(errors) == 1 and "point 1" in errors[0]
