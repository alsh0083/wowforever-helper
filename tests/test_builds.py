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
BUILDS = {b.id: b for b in load_builds(class_name="mage")}


def test_the_builds_exist_and_names_end_in_their_focus():
    assert set(BUILDS) == {"elementalist-v4", "elementalist-pve", "elementalist-pve-v2", "deep-frost",
                           "deep-fire", "arcane-pom-pyro", "fire-frost-shatter", "deep-arcane"}
    for b in BUILDS.values():
        assert b.variant in ("PvP", "PvE") and f"({b.variant}" in b.name


def test_elementalist_pair_shares_the_route_to_40():
    # #101: the revised PvE variant is the PvP build's pair; dual spec from 40 keeps levels 10-40
    pvp, pve = BUILDS["elementalist-v4"], BUILDS["elementalist-pve-v2"]
    assert pvp.pair == pve.pair == "offensive-elementalist"
    assert pve.origin == "model" and pve.name == "Offensive Elementalist (PvE)"
    assert pvp.order[:31] == pve.order[:31] and pvp.order[31:] != pve.order[31:]


def test_original_elementalist_pve_is_kept_for_comparison():
    old = BUILDS["elementalist-pve"]
    assert old.name == "Offensive Elementalist (PvE, original)" and old.pair == "elementalist-pve"
    assert old.order[:-1] == BUILDS["elementalist-v4"].order[:-1] and old.order[-1] == "Elemental Precision"


@pytest.mark.parametrize("build_id", sorted(BUILDS))
def test_build_uses_only_existing_talents(build_id):
    assert BUILDS[build_id].unknown_talents(CLS) == []


@pytest.mark.parametrize("build_id", sorted(BUILDS))
def test_final_allocation_is_legal_at_60(build_id):
    assert check_build(CLS, BUILDS[build_id].final_ids(CLS), level=60) == []


@pytest.mark.parametrize("build_id", ["deep-frost", "deep-fire", "arcane-pom-pyro"])
def test_reference_builds_spend_every_point(build_id):
    assert sum(BUILDS[build_id].final.values()) == points_available(60, CLS.rules)


@pytest.mark.parametrize("build_id", ["elementalist-v4", "elementalist-pve"])
def test_elementalist_order_is_legal_point_by_point_and_spends_60(build_id):
    b = BUILDS[build_id]
    assert check_order(CLS, b.order_ids(CLS)) == []
    assert len(b.order) == 51
    assert b.order.index("Ice Block") + 10 == 25 and b.order.index("Cold Snap") + 10 == 30


@pytest.mark.parametrize("build_id", sorted(BUILDS))
def test_must_have_by_levels_are_reachable(build_id):
    # the row gate alone: a row-r talent needs 5r points first, so it can't come before level 10 + 5r
    for name, level in BUILDS[build_id].must_have_by.items():
        assert level >= 10 + 5 * CLS.talent_named(name).row, name


def test_community_builds_cite_known_sources():
    from wowforever.consensus import Consensus
    sources = Consensus.load().sources
    community = [b for b in BUILDS.values() if b.origin == "community"]
    assert len(community) == 5
    for b in community:
        assert b.sources and all(s in sources for s in b.sources) and b.confidence in ("low", "medium", "high")
