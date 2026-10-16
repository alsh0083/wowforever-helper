"""Golden tests for non-mage immunity and pushback protection on the duel side (#337).

Immunity (Forever data, 1.60.1.70374): Divine Shield r1 10 s / r2 12 s (levels 34 / 50),
Divine Protection r1 6 s / r2 8 s (levels 6 / 18), all on a 300 s cooldown. They share
Forbearance, so the side takes the best one: share = immunity / cooldown, as the mage's Ice Block.
Pushback: talents tagged `pushback_pct` and listed for the class in config/pvp_self.toml
(`pushback_talents`) protect its damage casts: value at the taken rank / 100.
"""

import pytest

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.pvp.class_pvp import class_side
from wowforever.schema import Dataset, latest_dataset_path

DATASET = Dataset.load(latest_dataset_path())


def loaded(name):
    m = class_module(name)
    cls, problems = attach_effects(DATASET.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)
    assert problems == []
    return cls


def side(name, level, talents=()):
    cls = loaded(name)
    ranks = {cls.talent_named(n).talent_id: r for n, r in talents}
    return class_side(name, stat_table(name).at(level), cls.spells, cls, ranks)


@pytest.mark.parametrize(("name", "talent"), [
    ("priest", "Twilight Focus"),
    ("druid", "Nature's Focus"),
    ("shaman", "Eye of the Storm"),
    ("warlock", "Intensity"),
])
def test_pushback_talents_are_tagged(name, talent):
    effects = [e for e in loaded(name).talent_named(talent).effects if e.kind == "pushback_pct"]
    assert len(effects) == 1
    expected = (14.0, 28.0, 42.0, 56.0, 70.0) if name == "druid" else (23.0, 47.0, 70.0)
    assert tuple(effects[0].values) == expected


def test_paladin_takes_its_best_immunity():
    assert side("paladin", 60).immunity_share == pytest.approx(12 / 300)   # Divine Shield r2
    assert side("paladin", 40).immunity_share == pytest.approx(10 / 300)   # Divine Shield r1
    assert side("paladin", 20).immunity_share == pytest.approx(8 / 300)    # Divine Protection r2


@pytest.mark.parametrize("name", ["rogue", "warrior", "hunter", "priest", "warlock", "druid", "shaman"])
def test_classes_without_a_self_immunity(name):
    assert side(name, 60).immunity_share == 0.0


@pytest.mark.parametrize(("name", "talent", "rank", "expected"), [
    ("priest", "Twilight Focus", 3, 0.70),
    ("priest", "Twilight Focus", 1, 0.23),
    ("druid", "Nature's Focus", 5, 0.70),
    ("druid", "Nature's Focus", 2, 0.28),
    ("shaman", "Eye of the Storm", 2, 0.47),
    ("warlock", "Intensity", 3, 0.70),
])
def test_pushback_from_taken_talents(name, talent, rank, expected):
    assert side(name, 60, [(talent, rank)]).pushback == pytest.approx(expected)
    assert side(name, 60).pushback == 0.0


@pytest.mark.parametrize("name", ["rogue", "warrior", "hunter", "paladin"])
def test_classes_without_pushback_talents(name):
    assert side(name, 60).pushback == 0.0
