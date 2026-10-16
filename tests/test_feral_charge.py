"""Golden tests for Feral Charge in the druid's duel side (#342).

Forever data: Feral Charge (Bear) rank 1, 15 s cooldown; talent text: "immobilizing them and
interrupting any spell they are casting for 4 sec". It adds a 4 s root and a 4 s interrupt,
both only when the talent is taken.
Root seconds per minute: Entangling Roots 10 x 60/15 = 40, plus Feral Charge 4 x 60/15 = 16 -> 56.
"""

import pytest

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.pvp.class_pvp import class_side
from wowforever.pvp.duel import Control, lockout_seconds
from wowforever.schema import Dataset, latest_dataset_path

DATASET = Dataset.load(latest_dataset_path())


def side(talents=()):
    m = class_module("druid")
    cls, _ = attach_effects(DATASET.class_data("druid"), m.TALENT_EFFECTS, m.UNMODELED)
    ranks = {cls.talent_named(n).talent_id: 1 for n in talents}
    return class_side("druid", stat_table("druid").at(60), cls.spells, cls, ranks)


def test_without_the_talent_nothing_changes():
    s = side()
    assert s.root == pytest.approx(40.0)
    assert s.interrupt == 0.0


def test_feral_charge_roots_and_interrupts():
    s = side(["Feral Charge"])
    assert s.root == pytest.approx(56.0)
    expected = lockout_seconds([Control("interrupt", 4.0, 15.0)], 0)["interrupt"]
    assert expected > 0
    assert s.interrupt == pytest.approx(expected)
