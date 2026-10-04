"""The v0 builds (#20) must be legal on real Forever data (build 1.60.1.70205 fixtures)."""

from pathlib import Path

import pytest

from wowforever.builds import load_builds
from wowforever.classes.mage import LAYOUT
from wowforever.normalize import normalize_class, read_tables
from wowforever.rules import check_build, check_order, points_available
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
CLS, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205"), LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
BUILDS = {b.id: b for b in load_builds()}


def test_the_four_v0_builds_exist():
    assert set(BUILDS) == {"elementalist-v4", "deep-frost", "deep-fire", "arcane-pom-pyro"}


@pytest.mark.parametrize("build_id", sorted(BUILDS))
def test_build_uses_only_existing_talents(build_id):
    assert BUILDS[build_id].unknown_talents(CLS) == []


@pytest.mark.parametrize("build_id", sorted(BUILDS))
def test_final_allocation_is_legal_at_60(build_id):
    assert check_build(CLS, BUILDS[build_id].final_ids(CLS), level=60) == []


@pytest.mark.parametrize("build_id", ["deep-frost", "deep-fire", "arcane-pom-pyro"])
def test_reference_builds_spend_every_point(build_id):
    assert sum(BUILDS[build_id].final.values()) == points_available(60, CLS.rules)


def test_elementalist_order_is_legal_point_by_point_and_leaves_60_open():
    b = BUILDS["elementalist-v4"]
    assert check_order(CLS, b.order_ids(CLS)) == []
    assert len(b.order) == 50                     # level-60 point deliberately open
    assert b.order.index("Ice Block") + 10 == 25 and b.order.index("Cold Snap") + 10 == 30


@pytest.mark.parametrize("build_id", sorted(BUILDS))
def test_must_have_by_levels_are_reachable(build_id):
    # the row gate alone: a row-r talent needs 5r points first, so it can't come before level 10 + 5r
    for name, level in BUILDS[build_id].must_have_by.items():
        assert level >= 10 + 5 * CLS.talent_named(name).row, name
