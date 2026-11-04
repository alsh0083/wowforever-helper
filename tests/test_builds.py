"""The v0 builds (#20) must be legal on real Forever data: the dataset the model reads (config/dataset.toml)."""

from collections import Counter
from pathlib import Path

import pytest

from wowforever.builds import load_builds
from wowforever.rules import check_build, check_order, points_available
from wowforever.schema import Dataset, latest_dataset_path

CLS = Dataset.load(latest_dataset_path()).class_data("mage")
BUILDS = {b.id: b for b in load_builds(class_name="mage")}
# the owner's former hand-made Elementalist builds, dropped from the app 2026-10-07, kept as fixtures
FIXTURES = {b.id: b for b in load_builds(Path(__file__).parent / "fixtures" / "builds", class_name="mage")}


def test_the_builds_exist_and_names_end_in_their_focus():
    # 1.60.1.70755 (#460, #463): community standards only from a current source, model builds for the rest
    assert {k for k, b in BUILDS.items() if b.mode == "endgame"} == {
        "mage-arcane", "mage-fire",                                  # talentsforever.com's top builds
        "mage-frost-pve",                                            # seeded: no source publishes deep Frost
        "mage-arcane-pvp", "mage-fire-pvp", "mage-frost-pvp",        # tools/derive_slot_builds.py
        "mage-fire-model"}                                           # tools/derive_model_picks.py
    for b in BUILDS.values():
        assert b.variant in ("PvP", "PvE") and f"({b.variant}" in b.name


def test_the_former_elementalist_builds_stay_fixtures():
    # the owner's hand-made Elementalist route (#101) and its PvE pair left the app with the 70755 standards (#460)
    pvp = FIXTURES["elementalist-v4"]
    assert pvp.pair == "offensive-elementalist" and "elementalist-pve-v2" not in BUILDS

@pytest.mark.parametrize("build_id", sorted(BUILDS))
def test_build_uses_only_existing_talents(build_id):
    assert BUILDS[build_id].unknown_talents(CLS) == []


@pytest.mark.parametrize("build_id", sorted(BUILDS))
def test_final_allocation_is_legal_at_60(build_id):
    assert check_build(CLS, BUILDS[build_id].final_ids(CLS), level=60) == []


@pytest.mark.parametrize("build_id", sorted(k for k, b in BUILDS.items() if b.mode == "endgame"))
def test_endgame_builds_spend_every_point(build_id):
    assert sum(BUILDS[build_id].final.values()) == points_available(60, CLS.rules)


@pytest.mark.parametrize("build_id", sorted(BUILDS))
def test_must_have_by_levels_are_reachable(build_id):
    # the row gate alone: a row-r talent needs 5r points first, so it can't come before level 10 + 5r
    for name, level in BUILDS[build_id].must_have_by.items():
        assert level >= 10 + 5 * CLS.talent_named(name).row, name


def test_community_builds_cite_known_sources():
    from wowforever.consensus import Consensus
    sources = Consensus.load().sources
    community = [b for b in BUILDS.values() if b.origin == "community"]
    assert {b.id for b in community} == {"mage-arcane", "mage-fire"}      # talentsforever.com, 4 Nov (#460)
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
    assert {b.levels_into for b in leveling} == {"mage-arcane", "mage-fire", "mage-frost-pve", "mage-arcane-pvp",
                                                 "mage-fire-pvp", "mage-frost-pvp"}
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
