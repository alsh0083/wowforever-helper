"""Hunter rotation (#132, part 2). Expected values compose the physical-table functions (pinned by
test_physical.py) with the rotation's formulas, so each test pins one piece. Real Forever hunter
spells and talents (fixture build 1.60.1.70205), synthetic level-60 stats, level-63 boss, 3731 armor;
constants from config/hunter.toml (quiver +15%, normalized speeds ranged 2.8 / one-hand 2.4)."""

from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.classes.hunter_rotation import hunter_rotation
from wowforever.effects import attach_effects
from wowforever.melee_stats import MeleeStats
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells
from wowforever.physical import Attacker, Target, land_chance, ranged_shot, white_swing, yellow_attack
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
HUNTER = class_module("hunter")
TABLES = read_tables(FIX / "wago-1.60.1.70205-hunter")
RAW, _ = normalize_class(TABLES, HUNTER.LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "hunter.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
CLS, _ = attach_effects(RAW, HUNTER.TALENT_EFFECTS, HUNTER.UNMODELED)
SPELLS = class_spells(TABLES, skill_lines=HUNTER.SKILL_LINES)
BOSS = Target(level_diff=3, armor=3731)
STATS = MeleeStats(level=60, strength=60, agility=300, stamina=200, intellect=80, attack_power=500,
                   ranged_attack_power=800, crit_pct=12, ranged_crit_pct=12, hit_pct=4, health=3000,
                   mana=2000, main_hand=(80, 150, 2.4), off_hand=(60, 110, 1.9), ranged=(90, 160, 2.8))


def top(name):
    return max((s for s in SPELLS if s.name == name and s.level <= 60), key=lambda s: s.rank)


def test_untalented_ranged_rotation():
    rot = hunter_rotation(STATS, SPELLS, CLS, {}, BOSS)
    a = Attacker(60, 800, 12, 4)
    rapid = top("Rapid Fire")
    haste = 1.15 * (1 + rapid.haste_pct / 100 * rapid.duration / rapid.cooldown)
    auto = ranged_shot(125 + 800 / 14 * 2.8, a, BOSS) * haste / 2.8
    norm = 125 + 800 / 14 * 2.8
    aimed, multi, arcane = top("Aimed Shot"), top("Multi-Shot"), top("Arcane Shot")
    shots = (ranged_shot(norm + aimed.weapon_bonus, a, BOSS) / aimed.cooldown
             + ranged_shot(norm + multi.weapon_bonus, a, BOSS) / multi.cooldown
             + ranged_shot((arcane.min_damage + arcane.max_damage) / 2, a, BOSS) / arcane.cooldown)
    casting = aimed.cast_time / aimed.cooldown + multi.cast_time / multi.cooldown
    sting = top("Serpent Sting")
    dot = sting.periodic_damage * land_chance(a, BOSS, can_dodge=False) / sting.duration
    assert rot.ranged_dps == pytest.approx(auto * (1 - casting) + shots + dot)
    assert rot.mode == "ranged" and rot.pet_dps == 0


def test_untalented_melee_rotation():
    rot = hunter_rotation(STATS, SPELLS, CLS, {}, BOSS)
    a = Attacker(60, 500, 12, 4)
    mh = white_swing((80, 150, 2.4), a, BOSS, dual_wield=True)
    melee = mh / 2.4 + white_swing((60, 110, 1.9), a, BOSS, dual_wield=True, off_hand=True) / 1.9
    raptor = top("Raptor Strike")
    every = max(raptor.cooldown, 2.4)
    melee += (yellow_attack(115 + 500 / 14 * 2.4 + raptor.weapon_bonus, a, BOSS) - mh) / every
    for name in ("Mongoose Bite", "Strider Kick"):
        s = top(name)
        base = (115 + 500 / 14 * 2.4 + s.weapon_bonus) * (s.weapon_pct / 100 if s.weapon_pct else 1)
        melee += yellow_attack(base, a, BOSS) / s.cooldown
    assert rot.melee_dps == pytest.approx(melee)


def test_pet_adds_estimated_damage():
    rot = hunter_rotation(STATS, SPELLS, CLS, {}, BOSS, pet=True)
    assert rot.pet_dps == pytest.approx(1.2 * 60)
    assert rot.dps == pytest.approx(max(rot.ranged_dps, rot.melee_dps) + 1.2 * 60)


def ranks(*pairs):
    return {CLS.talent_named(n).talent_id: r for n, r in pairs}


def test_lone_wolf_survival_melee():
    talents = ranks(("Lone Wolf", 1), ("Predator's Edge", 5), ("Savage Strikes", 2), ("Lethal Attacks", 5),
                    ("Lacerating Strikes", 1), ("Lightning Reflexes", 5), ("Surefooted", 3))
    rot = hunter_rotation(STATS, SPELLS, CLS, talents, BOSS)
    extra_agi = 300 * 0.10
    ap = 500 + extra_agi
    a = Attacker(60, ap, 12 + 5 + extra_agi / 53 + 4, 4 + 3)
    mh = white_swing((80, 150, 2.4), a, BOSS, dual_wield=True, damage_pct=20, crit_damage_pct=30)
    melee = mh / 2.4 + white_swing((60, 110, 1.9), a, BOSS, dual_wield=True, off_hand=True,
                                   damage_pct=20 + 50, crit_damage_pct=30) / 1.9
    raptor = top("Raptor Strike")
    every = max(raptor.cooldown, 2.4)
    melee += (yellow_attack(115 + ap / 14 * 2.4 + raptor.weapon_bonus, a, BOSS, damage_pct=20,
                            crit_damage_pct=30) - mh) / every
    mb, sk = top("Mongoose Bite"), top("Strider Kick")
    melee += yellow_attack(115 + ap / 14 * 2.4 + mb.weapon_bonus, a, BOSS, damage_pct=20,
                           crit_damage_pct=30) * 1.4 / mb.cooldown
    melee += yellow_attack((115 + ap / 14 * 2.4) * sk.weapon_pct / 100, a, BOSS, damage_pct=20,
                           crit_damage_pct=30) / sk.cooldown
    assert rot.melee_dps == pytest.approx(melee)


def test_marksmanship_shot_talents():
    talents = ranks(("Lone Wolf", 1), ("Mortal Shots", 5), ("Barrage", 3), ("Ranged Weapon Specialization", 5),
                    ("Careful Aim", 5), ("Trueshot Aura", 1), ("Improved Arcane Shot", 5), ("Efficiency", 5))
    rot = hunter_rotation(STATS, SPELLS, CLS, talents, BOSS)
    rap = 800 + 80 + 30
    a = Attacker(60, rap, 12, 4)
    rapid = top("Rapid Fire")
    haste = 1.15 * (1 + rapid.haste_pct / 100 * rapid.duration / rapid.cooldown)
    auto = ranged_shot(125 + rap / 14 * 2.8, a, BOSS, damage_pct=5 + 20, crit_damage_pct=30) * haste / 2.8
    norm = 125 + rap / 14 * 2.8
    aimed, multi, arcane = top("Aimed Shot"), top("Multi-Shot"), top("Arcane Shot")
    shots = (ranged_shot(norm + aimed.weapon_bonus, a, BOSS, damage_pct=25 + 10, crit_damage_pct=30) / aimed.cooldown
             + ranged_shot(norm, a, BOSS, damage_pct=25 + 10, crit_damage_pct=30) / multi.cooldown
             + ranged_shot((arcane.min_damage + arcane.max_damage) / 2, a, BOSS, damage_pct=20,
                           crit_damage_pct=30) / (arcane.cooldown - 1.5))
    casting = aimed.cast_time / aimed.cooldown + multi.cast_time / multi.cooldown
    sting = top("Serpent Sting")
    dot = sting.periodic_damage * 1.2 * land_chance(a, BOSS, can_dodge=False) / sting.duration
    assert rot.ranged_dps == pytest.approx(auto * (1 - casting) + shots + dot)
    mana = (aimed.mana_cost / aimed.cooldown + multi.mana_cost / multi.cooldown
            + arcane.mana_cost / (arcane.cooldown - 1.5)) * 0.85 + sting.mana_cost * 0.85 / sting.duration
    assert rot.mode == "ranged" and rot.mana_per_second == pytest.approx(mana)
