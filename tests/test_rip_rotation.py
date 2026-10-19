"""Feral Rip (#397, part B): the energy cycle either ends every cycle with Ferocious Bite, or keeps Rip up (as
often as energy allows, at most once per its duration) and bites with the rest; the better plan wins."""

import pytest

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.druid_rotation import cat_rotation, finisher_dps
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path

D = class_module("druid")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("druid"), D.TALENT_EFFECTS, D.UNMODELED)


def test_bite_only_by_hand():
    # 5 builders at 40 energy and 100 damage, Bite 35 energy and 600: 10 energy/s buys 10/235 cycles of 1100
    assert finisher_dps(10.0, 5, 40.0, 100.0, 35.0, 600.0) == pytest.approx(10 / 235 * 1100)


def test_rip_when_energy_can_not_keep_it_up():
    # Rip (30 energy, 855 damage, 12 s): a Rip cycle costs 230; 10 energy/s affords 10/230 per second (< 1/12)
    assert finisher_dps(10.0, 5, 40.0, 100.0, 35.0, 600.0, rip=(30.0, 855.0, 12.0)) == pytest.approx(10 / 230 * 1355)


def test_rip_kept_up_and_bite_with_the_rest():
    # 25 energy/s: Rip every 12 s costs 230/12 = 19.17/s for 1355/12; Bite cycles with the 5.83 left
    left = 25 - 230 / 12
    assert finisher_dps(25.0, 5, 40.0, 100.0, 35.0, 600.0, rip=(30.0, 855.0, 12.0)) == pytest.approx(
        1355 / 12 + left / 235 * 1100)


def test_feral_rotation_uses_the_better_plan():
    ranks = {b.id: b.final_ids(CLS) for b in load_builds(class_name="druid")}["druid-feral"]
    stats = stat_table("druid").at(60).melee
    with_rip = cat_rotation(stats, CLS.spells, CLS, ranks, Target(3, 0))
    no_rip = cat_rotation(stats, [s for s in CLS.spells if s.name != "Rip"], CLS, ranks, Target(3, 0))
    assert with_rip.dps >= no_rip.dps and with_rip.white_dps == no_rip.white_dps
