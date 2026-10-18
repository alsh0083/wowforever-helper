"""Warrior Execute (#391): below 20% health all Rage goes to Execute, one per global cooldown (600 damage plus
10 per extra Rage, SpellEffect 20662 and its description); the rest of the fight runs the normal rotation."""

import pytest

from wowforever.calc.ev import GCD_SECONDS
from wowforever.classes import class_module
from wowforever.classes.warrior_rotation import execute_casts, warrior_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import Attacker, Target, yellow_attack
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warrior")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("warrior"), W.TALENT_EFFECTS, W.UNMODELED)
STATS = MeleeStatTable.load("warrior").at(60)
BOSS = Target(3, 0)


def test_execute_casts_by_hand():
    # 12 Rage/s: one Execute per 1.5 s GCD (0.667/s), each with 18 - 15 = 3 extra Rage
    rate, extra = execute_casts(12.0, 15.0, 1.5)
    assert rate == pytest.approx(1 / 1.5) and extra == pytest.approx(3.0)
    # 6 Rage/s: Rage-limited, 0.4/s, no extra
    assert execute_casts(6.0, 15.0, 1.5) == pytest.approx((0.4, 0.0))


def test_rotation_blends_the_execute_phase():
    without = warrior_rotation(STATS, [s for s in CLS.spells if s.name != "Execute"], CLS, {}, BOSS)
    with_execute = warrior_rotation(STATS, CLS.spells, CLS, {}, BOSS)
    rate, extra = execute_casts(without.rage_per_second, 15.0, GCD_SECONDS)
    a = Attacker(60, STATS.attack_power, STATS.crit_pct, STATS.hit_pct)
    hit = yellow_attack(600 + 10 * extra, a, BOSS)
    expected = 0.8 * without.dps + 0.2 * (without.white_dps + rate * hit)
    assert with_execute.dps == pytest.approx(expected)
    assert "Execute" in with_execute.abilities
