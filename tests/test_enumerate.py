"""Tests for the build enumerator (#15). The small-class tests compare against a brute-force
oracle (every rank combination, filtered with the legality checker), so expectations don't
depend on hand-counting."""

import itertools
import time
from pathlib import Path

import pytest

from wowforever.enumerate import enumerate_builds
from wowforever.rules import check_build
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


def oracle(cls, budget, trees, required=()):
    """Every legal build spending exactly `budget`, full ranks except at most one partial talent."""
    talents = [t for t in cls.talents if t.tree_id in trees]
    out = set()
    for ranks in itertools.product(*(range(t.max_rank + 1) for t in talents)):
        if sum(ranks) != budget:
            continue
        if sum(1 for t, r in zip(talents, ranks) if 0 < r < t.max_rank) > 1:
            continue
        build = {t.talent_id: r for t, r in zip(talents, ranks) if r}
        if any(build.get(tid) != cls.talent(tid).max_rank for tid in required):
            continue
        if check_build(cls, build, level=None) == []:
            out.add(frozenset(build.items()))
    return out


def as_set(builds):
    return {frozenset(b.items()) for b in builds}


@pytest.mark.parametrize("budget", [1, 5, 8, 11, 13, 16])
def test_matches_brute_force_over_both_trees(budget):
    assert as_set(enumerate_builds(CLS, budget=budget, trees=(1, 2))) == oracle(CLS, budget, (1, 2))


def test_tree_restriction():
    got = as_set(enumerate_builds(CLS, budget=10, trees=(1,)))
    assert got == oracle(CLS, 10, (1,))
    assert all(tid != X1 for b in got for tid, _ in b)


def test_required_talents_at_full_rank():
    got = as_set(enumerate_builds(CLS, budget=13, trees=(1, 2), required=(C1,)))
    assert got and got == oracle(CLS, 13, (1, 2), required=(C1,))


def test_no_duplicates_and_is_a_lazy_generator():
    gen = enumerate_builds(CLS, budget=11, trees=(1, 2))
    assert iter(gen) is gen
    builds = list(gen)
    assert len(builds) == len(as_set(builds))


def test_impossible_budget_yields_nothing():
    assert list(enumerate_builds(CLS, budget=17, trees=(1, 2))) == []


def test_real_mage_fire_frost_streams_quickly():
    from wowforever.classes.mage import LAYOUT
    from wowforever.normalize import normalize_class, read_tables
    from wowforever.sources.wowforevertalent import parse_page
    fix = Path(__file__).parent / "fixtures"
    cls, _ = normalize_class(read_tables(fix / "wago-1.60.1.70205"), LAYOUT,
                             parse_page((fix / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                             wago_build="1.60.1.70205")
    ice_block = cls.talent_named("Ice Block").talent_id
    start = time.perf_counter()
    first = list(itertools.islice(
        enumerate_builds(cls, budget=51, trees=(2, 3), required=(ice_block,)), 500))
    assert time.perf_counter() - start < 5.0
    assert len(first) == 500
    for b in first[:50]:
        assert sum(b.values()) == 51 and b[ice_block] == 1
        assert check_build(cls, b, level=60) == []
