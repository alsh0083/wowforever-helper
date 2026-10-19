"""Warrior Rend (#391): a bleed kept up on a single target (147 over 21 s for 10 Rage at rank 7), before Heroic
Strike; it lands or not, and armor doesn't reduce it. Improved Rend adds 35%."""

import pytest

from wowforever.classes import class_module
from wowforever.classes.warrior_rotation import warrior_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import Attacker, Target, land_chance
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warrior")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("warrior"), W.TALENT_EFFECTS,
                               W.UNMODELED)
STATS = MeleeStatTable.load("warrior").at(60)
BOSS = Target(3, 900)
RANKS = {CLS.talent_named("Improved Rend").talent_id: 3}


def test_rule():
    assert PROBLEMS == []
    (rule,) = CLS.talent_named("Improved Rend").effects
    assert (rule.kind, rule.applies_to, rule.values) == ("damage_pct", ("Rend",), (12.0, 23.0, 35.0))


def test_rend_part_by_hand():
    rend = best_rank(CLS.spells, "Rend", 60)
    parts = dict(warrior_rotation(STATS, CLS.spells, CLS, RANKS, BOSS).parts)
    land = land_chance(Attacker(60, STATS.attack_power, STATS.crit_pct, STATS.hit_pct), BOSS)
    assert parts["Rend"] == pytest.approx(rend.periodic_damage / rend.duration * land * 1.35)


def test_no_rend_against_a_pack():
    assert "Rend" not in dict(warrior_rotation(STATS, CLS.spells, CLS, RANKS, BOSS, pack=3).parts)
