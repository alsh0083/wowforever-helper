"""Rogue and hunter PvP sides (#134): their own controls with the opponents' energy and
diminishing-returns rules (config/pvp_self.toml), and armor against physical opponents."""

from pathlib import Path

import pytest

from wowforever.schema import latest_dataset_path
from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import armor_factor
from wowforever.pvp.class_pvp import class_side, pvp_score
from wowforever.pvp.duel import Control, load_kits, lockout_seconds
from wowforever.schema import Dataset

DATASET = latest_dataset_path()


def loaded(class_name):
    m = class_module(class_name)
    cls, _ = attach_effects(Dataset.load(DATASET).class_data(class_name), m.TALENT_EFFECTS, m.UNMODELED)
    return cls, MeleeStatTable.load(class_name).at(60)


def test_rogue_controls_share_energy_and_dr():
    cls, stats = loaded("rogue")
    side = class_side("rogue", stats, cls.spells, cls, {})
    # energy: Kidney 125*3 + Gouge 45*6 + Kick 25*6 + Blind 30*0.2 = 801 per minute > 300 budget
    f = 300 / 801
    cap6 = 60 * 1.75 * 6 / (1.75 * 6 + 15)
    cap10 = 60 * 1.75 * 10 / (1.75 * 10 + 15)
    stun = min((18 + 24) * f, cap6) + min(2 * f, cap10)        # stuns, then Blind's disorient
    assert side.stun == pytest.approx(stun)
    assert side.interrupt == pytest.approx(30 * f)
    assert side.physical_taken == pytest.approx(armor_factor(60, 2500) / armor_factor(60, 1000))


def test_lockout_seconds_matches_the_duel_rules():
    out = lockout_seconds([Control("stun", 6, 20), Control("stun", 4, 10), Control("interrupt", 5, 20)])
    assert out["stun"] == pytest.approx(60 * 10.5 / 25.5) and out["interrupt"] == pytest.approx(15)


def test_hunter_controls_follow_talents():
    cls, stats = loaded("hunter")
    builds = {b.id: b for b in load_builds(class_name="hunter")}
    bm = class_side("hunter", stats, cls.spells, cls, builds["hunter-beast-mastery"].final_ids(cls))
    mm = class_side("hunter", stats, cls.spells, cls, builds["hunter-marksmanship"].final_ids(cls))
    assert bm.stun > mm.stun                 # Intimidation is a Beast Mastery talent
    assert mm.interrupt == 0


@pytest.mark.parametrize("class_name", ["rogue", "hunter"])
def test_scores_are_duel_scores(class_name):
    cls, stats = loaded(class_name)
    for b in load_builds(class_name=class_name):
        assert 0 < pvp_score(class_name, stats, cls.spells, cls, b.final_ids(cls), load_kits()) < 1


def test_mages_are_opponents_now():
    assert "mage-frost" in {k.id for k in load_kits()}
