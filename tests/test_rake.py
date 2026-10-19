"""Feral Rake (#397): once per its duration Rake takes a builder's place: the same combo point, its hit plus a bleed
instead of the builder's damage, and the Energy it saves (or costs) is worth the cycle's damage per Energy."""

import pytest

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.druid_rotation import cat_rotation, rake_gain
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path

D = class_module("druid")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("druid"), D.TALENT_EFFECTS, D.UNMODELED)


def test_rake_gain_by_hand():
    # Rake 300 vs a 200 builder; builder 45 Energy, Rake 40: 5 Energy saved at 5 damage per Energy; every 9 s
    assert rake_gain(300.0, 200.0, 45.0, 40.0, 5.0, 9.0) == pytest.approx((100 + 25) / 9)
    # a weaker Rake loses: no gain is taken
    assert rake_gain(100.0, 200.0, 45.0, 40.0, 5.0, 9.0) == 0.0


def test_feral_rotation_with_rake():
    ranks = {b.id: b.final_ids(CLS) for b in load_builds(class_name="druid")}["druid-feral"]
    stats = stat_table("druid").at(60).melee
    with_rake = cat_rotation(stats, CLS.spells, CLS, ranks, Target(3, 0))
    no_rake = cat_rotation(stats, [s for s in CLS.spells if s.name != "Rake"], CLS, ranks, Target(3, 0))
    assert with_rake.dps >= no_rake.dps and with_rake.white_dps == no_rake.white_dps
