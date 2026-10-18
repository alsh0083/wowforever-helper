"""Warrior Overpower (#391): usable after the target dodges; it can't be dodged. Casts per second = the target's
dodges per second (white swings and abilities that can be dodged), at most one per cooldown, Rage permitting;
it goes after the cooldown abilities and before Heroic Strike."""

import pytest

from wowforever.classes import class_module
from wowforever.classes.warrior_rotation import overpower_rate, warrior_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warrior")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("warrior"), W.TALENT_EFFECTS, W.UNMODELED)
STATS = MeleeStatTable.load("warrior").at(60)
BOSS = Target(3, 0)


def test_overpower_rate_by_hand():
    # 0.5 attacks/s x 6.5% dodge = 0.0325 dodges/s, below one per 5 s; plenty of Rage
    assert overpower_rate(0.5, 0.065, 5.0, 100.0, 5.0) == pytest.approx(0.0325)
    # 4 attacks/s x 6.5% = 0.26/s, capped at 1/5 s
    assert overpower_rate(4.0, 0.065, 5.0, 100.0, 5.0) == pytest.approx(0.2)
    # Rage-limited: 0.1 Rage/s left buys 0.02 Overpowers/s
    assert overpower_rate(0.5, 0.065, 5.0, 0.1, 5.0) == pytest.approx(0.02)


def test_rotation_casts_overpower():
    r = warrior_rotation(STATS, CLS.spells, CLS, {}, BOSS)
    without = warrior_rotation(STATS, [s for s in CLS.spells if s.name != "Overpower"], CLS, {}, BOSS)
    assert "Overpower" in r.abilities and r.dps > without.dps
