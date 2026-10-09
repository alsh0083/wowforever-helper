"""The v0 builds (#20) must be legal on real Forever data (build 1.60.1.70205 fixtures)."""

from collections import Counter
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
# the owner's former hand-made Elementalist builds, dropped from the app 2026-10-07, kept as fixtures
FIXTURES = {b.id: b for b in load_builds(Path(__file__).parent / "fixtures" / "builds", class_name="mage")}


def test_the_builds_exist_and_names_end_in_their_focus():
    assert {k for k, b in BUILDS.items() if b.mode == "endgame"} == {"elementalist-pve-v2", "deep-frost",
                           "deep-fire", "arcane-pom-pyro", "fire-frost-shatter", "deep-arcane",
                           # matrix fill (owner request, 2026-10-05): catalog plan and model builds
                           "mage-frost-pve", "mage-arcane-pvp", "mage-fire-pvp", "mage-fire-frost-pvp",
                           "mage-arcane-fire-pve",
                           # model picks next to the standards they beat (owner request, 2026-10-07)
                           "deep-arcane-model", "mage-frost-pve-model"}
    for b in BUILDS.values():
        assert b.variant in ("PvP", "PvE") and f"({b.variant}" in b.name


def test_elementalist_pair_shares_the_route_to_40():
    # #101: the revised PvE variant is the PvP build's pair; dual spec from 40 keeps levels 10-40
    pvp, pve = FIXTURES["elementalist-v4"], BUILDS["elementalist-pve-v2"]
    assert pvp.pair == pve.pair == "offensive-elementalist"
    assert pve.origin == "model" and pve.name == "Offensive Elementalist (PvE)"
    assert pvp.order[:31] == pve.order[:31] and pvp.order[31:] != pve.order[31:]


@pytest.mark.parametrize("build_id", sorted(BUILDS))
def test_build_uses_only_existing_talents(build_id):
    assert BUILDS[build_id].unknown_talents(CLS) == []


@pytest.mark.parametrize("build_id", sorted(BUILDS))
def test_final_allocation_is_legal_at_60(build_id):
    assert check_build(CLS, BUILDS[build_id].final_ids(CLS), level=60) == []


@pytest.mark.parametrize("build_id", ["deep-frost", "deep-fire", "arcane-pom-pyro"])
def test_reference_builds_spend_every_point(build_id):
    assert sum(BUILDS[build_id].final.values()) == points_available(60, CLS.rules)


def test_elementalist_order_is_legal_point_by_point_and_spends_60():
    b = BUILDS["elementalist-pve-v2"]
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
    assert len(community) == 6          # 5 from #23 plus the catalog's Frost PvE plan
    for b in community:
        assert b.sources and all(s in sources for s in b.sources) and b.confidence in ("low", "medium", "high")


def test_model_filled_points_add_to_the_published_final(tmp_path):
    from wowforever.builds import Build

    path = tmp_path / "b.toml"
    path.write_text('id = "b"\nname = "B (PvE)"\nsummary = "s"\norigin = "community"\n\n[final]\n"Ice Shards" = 3\n\n'
                    '[model_filled]\n"Ice Shards" = 2\n"Frostbite" = 1\n', encoding="utf-8")
    b = Build.load(path)
    assert b.final == {"Ice Shards": 5, "Frostbite": 1} and b.model_filled == {"Ice Shards": 2, "Frostbite": 1}


def test_leveling_builds_follow_their_endgame_build_with_few_detours():
    # owner feedback, 2026-10-07: a leveling build is its endgame build's path, plus at most 7
    # leveling-only points at a time (respecced at 60)
    leveling = [b for b in BUILDS.values() if b.mode == "leveling"]
    assert {b.levels_into for b in leveling} >= {"deep-frost", "fire-frost-shatter", "mage-fire-frost-pvp"}
    for b in leveling:
        target = BUILDS[b.levels_into].final_ids(CLS)
        ids = b.order_ids(CLS)
        assert check_order(CLS, ids) == [] and len(ids) == points_available(60, CLS.rules), b.id
        ranks = Counter()
        for tid in ids:
            ranks[tid] += 1
            assert sum(max(0, n - target.get(t, 0)) for t, n in ranks.items()) <= 7, b.id


def test_renamed_talents_resolve_under_either_name():
    from wowforever.schema import talent_aliases

    assert talent_aliases("Natural Instinct") == {"natural instinct", "predatory instincts"}
    assert talent_aliases("Predatory Instincts") == {"natural instinct", "predatory instincts"}
    assert talent_aliases("Frostbite") == {"frostbite"}
