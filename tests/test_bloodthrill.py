"""Bloodthrill (#391): main-hand melee attacks against the Rend target have a chance to enable Overpower. Rend is kept
up on one target, so each landed main-hand swing adds that chance of an Overpower activation on top of the dodges,
still at most one Overpower per cooldown and as Rage allows."""

import pytest

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.warrior_rotation import overpower_rate, warrior_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warrior")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("warrior"), W.TALENT_EFFECTS,
                               W.UNMODELED)
STATS = MeleeStatTable.load("warrior").at(60)
BOSS = Target(3, 3731)
ARMS = next(b for b in load_builds(class_name="warrior") if b.id == "warrior-arms").final_ids(CLS)
BT = CLS.talent_named("Bloodthrill").talent_id


def test_rule():
    assert PROBLEMS == []
    (rule,) = CLS.talent_named("Bloodthrill").effects
    assert (rule.kind, rule.applies_to, rule.values) == ("proc_chance", ("@bloodthrill",), (4.0, 8.0, 12.0, 16.0, 20.0))


def test_extra_activations_by_hand():
    # 0.5 attacks/s x 6.5% dodge = 0.0325, plus 0.05 from Bloodthrill = 0.0825 (under 1 per 5 s and the Rage)
    assert overpower_rate(0.5, 0.065, 5.0, 100.0, 5.0, 0.05) == pytest.approx(0.0825)
    # still at most one per cooldown
    assert overpower_rate(0.5, 0.065, 5.0, 100.0, 5.0, 0.5) == pytest.approx(0.2)
    # the old call is unchanged
    assert overpower_rate(0.5, 0.065, 5.0, 100.0, 5.0) == pytest.approx(0.0325)


def test_arms_overpowers_more_with_bloodthrill():
    assert ARMS[BT] == 5
    without = {t: r for t, r in ARMS.items() if t != BT}
    with_bt = dict(warrior_rotation(STATS, CLS.spells, CLS, ARMS, BOSS).parts)
    no_bt = dict(warrior_rotation(STATS, CLS.spells, CLS, without, BOSS).parts)
    assert with_bt["Overpower"] > no_bt["Overpower"]


def test_needs_rend():
    no_rend = [s for s in CLS.spells if s.name != "Rend"]
    without = {t: r for t, r in ARMS.items() if t != BT}
    with_bt = dict(warrior_rotation(STATS, no_rend, CLS, ARMS, BOSS).parts)
    no_bt = dict(warrior_rotation(STATS, no_rend, CLS, without, BOSS).parts)
    assert with_bt["Overpower"] == pytest.approx(no_bt["Overpower"])
