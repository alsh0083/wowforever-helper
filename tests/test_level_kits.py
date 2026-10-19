"""Opponent kits at the duel's level (#272): PvP below 60 no longer duels level-60 opponents.

A kit's level-L health, DPS and opener damage are its config [at_60] values scaled by the damage
engine's ratio between level L and level 60 for the kit's community build, so level 60 is exactly
the config. At level L a build has L - 9 talent points (the first point comes at 10).
"""

import pytest

from wowforever.builds import load_builds
from wowforever.pvp.duel import load_kits
from wowforever.pvp.kit_stats import KIT_BUILDS, engine_at, engine_at_60, kit_ranks_at
from wowforever.schema import Dataset, latest_dataset_path

DS = Dataset.load(latest_dataset_path())


def test_engine_at_60_is_the_existing_level_60_engine():
    assert engine_at("rogue-combat", 60) == pytest.approx(engine_at_60("rogue-combat"))


def test_a_level_30_kit_is_weaker_than_at_60():
    h30, d30 = engine_at("warrior-arms", 30)
    h60, d60 = engine_at("warrior-arms", 60)
    assert 0 < h30 < h60 and 0 < d30 < d60


def test_kit_ranks_at_a_level_spend_level_minus_9_points_within_the_final_build():
    cls = DS.class_data("rogue")
    build = {b.id: b for b in load_builds(class_name="rogue")}[KIT_BUILDS["rogue-combat"]]
    final = build.final_ids(cls)
    for level in (10, 30, 60):
        ranks = kit_ranks_at(build, cls, level)
        assert sum(ranks.values()) == min(level - 9, sum(final.values()))
        assert all(0 < r <= final[tid] for tid, r in ranks.items())
    assert kit_ranks_at(build, cls, 60) == final


def test_ranks_follow_the_build_order_when_it_has_one():
    cls = DS.class_data("rogue")
    build = next(b for b in load_builds(class_name="rogue") if b.order)
    expected: dict[int, int] = {}
    for tid in build.order_ids(cls)[:21]:
        expected[tid] = expected.get(tid, 0) + 1
    assert kit_ranks_at(build, cls, 30) == expected


def test_load_kits_at_60_is_the_config():
    by_id = {k.id: k for k in load_kits()}
    assert {k.id: k for k in load_kits(60)} == by_id
    assert by_id["warrior-arms"].health == 3580 and by_id["warrior-arms"].at_level == 60


def test_load_kits_below_60_scales_engine_kits_and_keeps_the_rest():
    at60 = {k.id: k for k in load_kits(60)}
    at30 = {k.id: k for k in load_kits(30)}
    h30, d30 = engine_at("warrior-arms", 30)
    h60, d60 = engine_at("warrior-arms", 60)
    arms = at30["warrior-arms"]
    assert arms.at_level == 30
    assert arms.health == pytest.approx(at60["warrior-arms"].health * h30 / h60)
    assert arms.dps == pytest.approx(at60["warrior-arms"].dps * d30 / d60)
    assert arms.opener_damage == pytest.approx(at60["warrior-arms"].opener_damage * d30 / d60)
    frost = at30["mage-frost"]                       # no engine build for the mage kit: level-60 values, flagged
    assert frost.at_level == 60 and frost.health == at60["mage-frost"].health
    assert [k.id for k in load_kits(30)] == [k.id for k in load_kits(60)]
