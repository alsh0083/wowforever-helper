"""Rogue rotation (#131, part 3). Spec: docs/tasks/131-rogue-rotation.md.

Expected values compose the physical-table functions (pinned by test_physical.py) with the spec's
cycle formulas, so each test pins one piece. Real Forever rogue spells and talents (fixture build
1.60.1.70205), synthetic level-60 stats, level-63 boss with 3731 armor."""

from dataclasses import replace
from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.classes.rogue_rotation import rogue_rotation
from wowforever.effects import attach_effects
from wowforever.melee_stats import MeleeStats
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells
from wowforever.physical import Attacker, Target, white_swing, yellow_attack
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
ROGUE = class_module("rogue")
TABLES = read_tables(FIX / "wago-1.60.1.70205-rogue")
RAW, _ = normalize_class(TABLES, ROGUE.LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "rogue.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
CLS, _ = attach_effects(RAW, ROGUE.TALENT_EFFECTS, ROGUE.UNMODELED)
SPELLS = class_spells(TABLES, skill_lines=ROGUE.SKILL_LINES)
STATS = MeleeStats(level=60, strength=100, agility=200, stamina=100, intellect=30, attack_power=600,
                   ranged_attack_power=300, crit_pct=15, ranged_crit_pct=15, hit_pct=3, health=3000,
                   mana=0, main_hand=(100, 200, 2.6), off_hand=(60, 110, 1.8), ranged=None)
BOSS = Target(level_diff=3, armor=3731)


def top(name):
    return max((s for s in SPELLS if s.name == name and s.level <= 60), key=lambda s: s.rank)


def ranks(**by_name):
    return {CLS.talent_named(n.replace("_", " ")).talent_id: r for n, r in by_name.items()}


def cycle(n_builder_ev, builder_cost, cp, evis_ev, energy, start=0.0, refund=0.0, snd_seconds=21.0):
    n = (5 - start) / cp
    r = energy / (n * builder_cost + 35 - refund)
    f = max(0.0, 1 - (1 / snd_seconds) / r)
    return r, r * (n * n_builder_ev + f * evis_ev)


def test_untalented_rogue_sinister_strike_cycle():
    rot = rogue_rotation(STATS, SPELLS, CLS, {}, BOSS)
    a = Attacker(60, 600, 15, 3)
    white = (white_swing((100, 200, 2.6), a, BOSS, dual_wield=True) * 1.3 / 2.6
             + white_swing((60, 110, 1.8), a, BOSS, dual_wield=True, off_hand=True) * 1.3 / 1.8)
    ss = top("Sinister Strike")
    builder = yellow_attack(150 + 600 / 14 * 2.4 + ss.weapon_bonus, a, BOSS)
    evis = top("Eviscerate")
    evis_ev = yellow_attack((evis.min_damage + evis.max_damage) / 2 + evis.per_combo_point * 5, a, BOSS)
    land = (100 - (8 - 2) - 6.5) / 100                          # hit 3 - suppression 1 = 2 off the 8% miss
    r, yellow = cycle(builder, ss.energy_cost, land, evis_ev, 10.0)
    assert rot.builder == "Sinister Strike"
    assert rot.white_dps == pytest.approx(white)
    assert rot.yellow_dps == pytest.approx(yellow)
    assert rot.cycles_per_second == pytest.approx(r)
    assert rot.dps == pytest.approx(white + yellow)


def test_combat_talents():
    talents = ranks(Malice=5, Precision=3, Lethality=5, Aggression=3, Seal_Fate=5, Ruthlessness=3,
                    Relentless_Strikes=1, Improved_Sinister_Strike=2, Dual_Wield_Specialization=5,
                    Adrenaline_Rush=1, Blade_Flurry=1, Improved_Slice_and_Dice=3, Improved_Eviscerate=3,
                    Weapon_Expertise=2)
    rot = rogue_rotation(STATS, SPELLS, CLS, talents, BOSS)
    a = Attacker(60, 600, 15 + 5, 3 + 3)
    h = 1.3 * (1 + 0.20 * 15 / 120)
    white = (white_swing((100, 200, 2.6), a, BOSS, dual_wield=True, dodge_reduction=2) * h / 2.6
             + white_swing((60, 110, 1.8), a, BOSS, dual_wield=True, off_hand=True, damage_pct=25,
                           dodge_reduction=2) * h / 1.8)
    ss = top("Sinister Strike")
    builder = yellow_attack(150 + 600 / 14 * 2.4 + ss.weapon_bonus, a, BOSS, damage_pct=6,
                            crit_damage_pct=20, dodge_reduction=2)
    evis = top("Eviscerate")
    evis_ev = yellow_attack((evis.min_damage + evis.max_damage) / 2 + evis.per_combo_point * 5, a, BOSS,
                            damage_pct=6 + 20, dodge_reduction=2)
    land = (100 - (8 - 5) - (6.5 - 2)) / 100
    crit = (20 - 1.8) / 100
    cp = land + land * crit                                     # Seal Fate 100%
    energy = 10 * (1 + 1.0 * 15 / 300)
    snd = top("Slice and Dice")
    snd_seconds = (snd.duration + 3 * 5) * 1.45
    r, yellow = cycle(builder, ss.energy_cost - 5, cp, evis_ev, energy, start=0.6, refund=0.2 * 5 * 25,
                      snd_seconds=snd_seconds)
    assert rot.white_dps == pytest.approx(white)
    assert rot.yellow_dps == pytest.approx(yellow)


def test_mutilate_strikes_with_both_hands():
    talents = ranks(Mutilate=1, Seal_Fate=5)
    rot = rogue_rotation(STATS, SPELLS, CLS, talents, BOSS)
    assert rot.builder == "Mutilate"
    a = Attacker(60, 600, 15, 3)
    mut = top("Mutilate")
    mh = (150 + 600 / 14 * 1.7 + mut.weapon_bonus) * mut.weapon_pct / 100
    oh = (85 + 600 / 14 * 1.7 + mut.weapon_bonus) * mut.weapon_pct / 100
    builder = yellow_attack(mh, a, BOSS) + yellow_attack(oh, a, BOSS)
    land = (100 - 6 - 6.5) / 100
    c = (15 - 1.8) / 100
    cp = mut.combo_points * land + land * (1 - (1 - c) ** 2)
    evis = top("Eviscerate")
    evis_ev = yellow_attack((evis.min_damage + evis.max_damage) / 2 + evis.per_combo_point * 5, a, BOSS)
    _, yellow = cycle(builder, mut.energy_cost, cp, evis_ev, 10.0)
    assert rot.yellow_dps == pytest.approx(yellow)


def test_armor_penetration_lowers_target_armor():
    plain = rogue_rotation(STATS, SPELLS, CLS, {}, BOSS)
    pen = rogue_rotation(STATS, SPELLS, CLS, ranks(Serrated_Blades=3), BOSS)
    same = rogue_rotation(STATS, SPELLS, CLS, {}, replace(BOSS, armor=3731 * 0.91))
    assert pen.dps == pytest.approx(same.dps) and pen.dps > plain.dps
