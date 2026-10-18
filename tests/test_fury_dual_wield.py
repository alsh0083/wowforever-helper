"""Fury dual wield, part B (#391): off-hand swings (dual-wield miss, half damage, Dual Wield Specialization +25%
damage and +50% Rage, Furious Precision +10% off-hand hit), Bloodthirst (48 + 45% of attack power) in the priority,
and the better of the two-hander and the [warrior_dw] table's weapons for each fight."""

from dataclasses import replace

import pytest

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.warrior_rotation import warrior_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import Attacker, Target, white_swing
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warrior")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("warrior"), W.TALENT_EFFECTS,
                               W.UNMODELED)
DW = MeleeStatTable.load("warrior_dw").at(60)
BOSS = Target(3, 0)
BUILDS = {b.id: b.final_ids(CLS) for b in load_builds(class_name="warrior")}


def only(name, rank):
    return {CLS.talent_named(name).talent_id: rank}


def test_rules():
    assert PROBLEMS == []
    dws = {(e.kind, e.applies_to): e.values[-1] for e in CLS.talent_named("Dual Wield Specialization").effects}
    assert dws == {("damage_pct", ("@off_hand",)): 25.0, ("resource_pct", ("@off_hand",)): 50.0}
    (fp,) = CLS.talent_named("Furious Precision").effects
    assert (fp.kind, fp.applies_to, fp.values[-1]) == ("hit_chance", ("@off_hand",), 10.0)


def test_white_damage_from_both_hands():
    a = Attacker(60, DW.attack_power, DW.crit_pct, DW.hit_pct)
    mh = white_swing(DW.main_hand, a, BOSS, dual_wield=True) / DW.main_hand[2]
    oh = white_swing(DW.off_hand, a, BOSS, dual_wield=True, off_hand=True) / DW.off_hand[2]
    assert warrior_rotation(DW, CLS.spells, CLS, {}, BOSS).white_dps == pytest.approx(mh + oh)


def test_dual_wield_specialization_and_furious_precision():
    a = Attacker(60, DW.attack_power, DW.crit_pct, DW.hit_pct)
    oh = white_swing(DW.off_hand, a, BOSS, dual_wield=True, off_hand=True) / DW.off_hand[2]
    oh_spec = white_swing(DW.off_hand, a, BOSS, dual_wield=True, off_hand=True, damage_pct=25.0) / DW.off_hand[2]
    base = warrior_rotation(DW, CLS.spells, CLS, {}, BOSS)
    spec = warrior_rotation(DW, CLS.spells, CLS, only("Dual Wield Specialization", 5), BOSS)
    assert spec.white_dps - base.white_dps == pytest.approx(oh_spec - oh)
    assert spec.rage_per_second > base.rage_per_second
    aimed = replace(a, hit_pct=a.hit_pct + 10)
    oh_hit = white_swing(DW.off_hand, aimed, BOSS, dual_wield=True, off_hand=True) / DW.off_hand[2]
    precise = warrior_rotation(DW, CLS.spells, CLS, only("Furious Precision", 3), BOSS)
    assert precise.white_dps - base.white_dps == pytest.approx(oh_hit - oh)


def test_two_hander_unchanged_without_an_off_hand():
    two = MeleeStatTable.load("warrior").at(60)
    a = Attacker(60, two.attack_power, two.crit_pct, two.hit_pct)
    assert warrior_rotation(two, CLS.spells, CLS, {}, BOSS).white_dps == pytest.approx(
        white_swing(two.main_hand, a, BOSS) / two.main_hand[2])


def test_dual_wield_swaps_only_the_weapons():
    stats = MeleeStatTable.load("warrior").at(60)
    dual = W.dual_wield(stats)
    assert (dual.main_hand, dual.off_hand) == (DW.main_hand, DW.off_hand)
    assert dual.attack_power == stats.attack_power                       # only the weapons change


@pytest.mark.parametrize("build", ["warrior-fury-pve", "warrior-arms"])
def test_output_takes_the_better_weapon_set(build):
    # owner (2026-10-17): assume the best weapons for the scenario, so two-hander or dual wield, whichever wins
    from wowforever.weapon_talents import best_weapon

    ranks = BUILDS[build]
    stats = MeleeStatTable.load("warrior").at(60)
    runs = [best_weapon(lambda s, t: warrior_rotation(s, CLS.spells, CLS, ranks, t), row, BOSS, CLS, ranks)[0]
            for row in (stats, W.dual_wield(stats))]
    assert W.output(stats, CLS.spells, CLS, ranks, BOSS).dps == pytest.approx(max(r.dps for r in runs))


def test_fury_uses_bloodthirst():
    r = warrior_rotation(W.dual_wield(MeleeStatTable.load("warrior").at(60)), CLS.spells, CLS,
                         BUILDS["warrior-fury-pve"], BOSS)
    assert "Bloodthirst" in r.abilities and "Mortal Strike" not in r.abilities
