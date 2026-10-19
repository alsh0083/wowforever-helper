"""Warrior Slam with Improved Slam (#391): it no longer delays the swing and its cooldown is 3 s shorter (18 -> 15),
so it joins the cooldown abilities after Whirlwind. Without Improved Slam it stays out (it would delay swings)."""

import pytest

from wowforever.classes import class_module
from wowforever.classes.warrior_rotation import warrior_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import Attacker, Target, yellow_attack
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warrior")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("warrior"), W.TALENT_EFFECTS,
                               W.UNMODELED)
STATS = MeleeStatTable.load("warrior").at(60)
BOSS = Target(3, 0)
SLAM = {CLS.talent_named("Improved Slam").talent_id: 2}


def test_rule():
    assert PROBLEMS == []
    (rule,) = CLS.talent_named("Improved Slam").effects
    assert (rule.kind, rule.applies_to, rule.values) == ("cooldown", ("Slam",), (-3.0, -3.0))


def test_slam_needs_improved_slam():
    assert "Slam" not in warrior_rotation(STATS, CLS.spells, CLS, {}, BOSS).abilities
    r = warrior_rotation(STATS, CLS.spells, CLS, SLAM, BOSS)
    assert "Slam" in r.abilities


def test_slam_part_by_hand():
    slam = best_rank(CLS.spells, "Slam", 60)
    a = Attacker(60, STATS.attack_power, STATS.crit_pct, STATS.hit_pct)
    weapon = STATS.main_hand
    base = (weapon[0] + weapon[1]) / 2 + STATS.attack_power / 14 * weapon[2] + slam.weapon_bonus
    parts = dict(warrior_rotation(STATS, CLS.spells, CLS, SLAM, BOSS).parts)
    # at most once per 15 s; less when Rage runs short after Whirlwind
    assert 0 < parts["Slam"] <= yellow_attack(base, a, BOSS) / (slam.cooldown - 3) + 1e-9
