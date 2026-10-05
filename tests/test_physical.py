"""Physical combat table (#130): expected damage of white swings, yellow attacks and ranged shots.
Spec: docs/tasks/130-physical.md; constants: config/physical.toml. Hand-worked values below.

Shared attacker: level 60, 1000 attack power, 20% crit, 5% hit; weapon 100-200 at 2.0 s, so a swing's
base is 150 + 1000/14 * 2 = 292.857. Boss: 3 levels up, 3731 armor, so the armor factor is
1 - 3731 / (3731 + 400 + 85 * 60) = 1 - 3731/9231."""

import pytest

from wowforever.physical import Attacker, Target, armor_factor, ranged_shot, white_swing, yellow_attack

A = Attacker(level=60, attack_power=1000, crit_pct=20, hit_pct=5)
WEAPON = (100, 200, 2.0)
BASE = 150 + 1000 / 14 * 2
BOSS = Target(level_diff=3, armor=3731)
ARMOR = 1 - 3731 / 9231


def test_armor_factor():
    assert armor_factor(60, 3731) == pytest.approx(ARMOR)
    assert armor_factor(60, 0) == 1.0


def test_white_swing_against_an_even_target():
    # miss 5 - 5 = 0, dodge 5, glancing 10, crit 20, hit 65
    ev = white_swing(WEAPON, A, Target(level_diff=0))
    assert ev == pytest.approx(BASE * (65 + 10 * 0.65 + 20 * 2) / 100)


def test_dual_wield_white_swing_against_a_boss():
    # hit 5 - suppression 1 = 4; miss 8 + 19 - 4 = 23; dodge 6.5; glancing 40; crit 20 - 1.8 = 18.2
    # hit = 100 - 23 - 6.5 - 40 - 18.2 = 12.3
    mult = (12.3 + 40 * 0.65 + 18.2 * 2) / 100
    assert white_swing(WEAPON, A, BOSS, dual_wield=True) == pytest.approx(BASE * mult * ARMOR)
    assert white_swing(WEAPON, A, BOSS, dual_wield=True, off_hand=True) == pytest.approx(BASE * 0.5 * mult * ARMOR)


def test_white_crit_is_capped_by_the_one_roll_table():
    hot = Attacker(level=60, attack_power=1000, crit_pct=90, hit_pct=5)
    # room left for crits: 100 - 23 - 6.5 - 40 = 30.5, and no plain hits
    mult = (40 * 0.65 + 30.5 * 2) / 100
    assert white_swing(WEAPON, hot, BOSS, dual_wield=True) == pytest.approx(BASE * mult * ARMOR)


def test_yellow_attack_rolls_crit_on_landed_hits():
    # miss 8 - 4 = 4, dodge 6.5 -> 89.5% land; crit 18.2%
    ev = yellow_attack(500, A, BOSS)
    assert ev == pytest.approx(500 * 0.895 * (1 + 0.182) * ARMOR)
    # +10% damage and +30% crit chance from talents
    assert yellow_attack(500, A, BOSS, damage_pct=10, crit_bonus=30) == pytest.approx(
        500 * 1.1 * 0.895 * (1 + 0.482) * ARMOR)


def test_ranged_shots_cannot_be_dodged():
    assert ranged_shot(500, A, BOSS) == pytest.approx(500 * 0.96 * 1.182 * ARMOR)


def test_level_differences_past_three_use_the_boss_row():
    assert white_swing(WEAPON, A, Target(level_diff=5, armor=3731)) == pytest.approx(
        white_swing(WEAPON, A, BOSS))
