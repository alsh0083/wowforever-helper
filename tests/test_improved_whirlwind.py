"""Improved Whirlwind (#465, 1.60.1.70755): -1/-2 s cooldown and +15/30% damage to the closest enemy. A Whirlwind
that hits n mobs deals n - 1 + 1.30 times one hit at rank 2, so with Rage to spare 3 mobs over 2 is 3.3/2.3."""

import pytest

from wowforever import melee_scenarios as ms
from wowforever.classes import class_module
from wowforever.classes import warrior_rotation as wr
from wowforever.effects import attach_effects
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warrior")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("warrior"), W.TALENT_EFFECTS, W.UNMODELED)
STATS = ms.stat_table("warrior").at(60)
MOBS = Target(0, 3300)
IW = CLS.talent_named("Improved Whirlwind").talent_id


def whirlwind(ranks, pack):
    return dict(wr.warrior_rotation(STATS, CLS.spells, CLS, ranks, MOBS, pack=pack).parts)["Whirlwind"]


def test_rule():
    assert PROBLEMS == []
    assert [(e.kind, e.applies_to, e.values) for e in CLS.talent_named("Improved Whirlwind").effects] == [
        ("cooldown", ("Whirlwind",), (-1.0, -2.0)), ("damage_pct", ("@closest_Whirlwind",), (15.0, 30.0))]


def test_the_closest_enemy_takes_more():
    assert whirlwind({IW: 2}, 3) / whirlwind({IW: 2}, 2) == pytest.approx(3.3 / 2.3)
    assert whirlwind({IW: 1}, 3) / whirlwind({IW: 1}, 2) == pytest.approx(3.15 / 2.15)
    assert whirlwind({IW: 2}, 5) == pytest.approx(whirlwind({IW: 2}, 4))                # 4 targets at most
    assert whirlwind({}, 3) / whirlwind({}, 2) == pytest.approx(3 / 2)                  # without the talent
