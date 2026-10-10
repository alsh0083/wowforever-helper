"""Warrior on the melee engine (#162): two-hander stat table, Rage rotation, effect rules, scenarios,
PvP side and report."""

import json
from pathlib import Path

import pytest

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.warrior_rotation import rage_conversion, warrior_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable, questing
from wowforever.melee_stats import class_config
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells
from wowforever.physical import Target
from wowforever.pvp.class_pvp import class_side
from wowforever.scenarios import best_rank
from wowforever.sources.wowforevertalent import parse_page

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
W = class_module("warrior")
TABLES = read_tables(FIX / "wago-1.60.1.70291-warrior")
RAW, _ = normalize_class(TABLES, W.LAYOUT, parse_page((FIX / "wowforevertalent" / "warrior.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70291")
CLS, REPORT = attach_effects(RAW, W.TALENT_EFFECTS, W.UNMODELED)
SPELLS = class_spells(TABLES, skill_lines=W.SKILL_LINES)
STATS = MeleeStatTable.load("warrior").at(60)
BUILDS = {b.id: b for b in load_builds(class_name="warrior")}
ARMS = BUILDS["warrior-arms"].final_ids(CLS)
BOSS = Target(3, 976)


def without(ranks, name):
    tid = CLS.talent_named(name).talent_id
    return {t: r for t, r in ranks.items() if t != tid}


def test_stat_table_swings_a_two_hander_with_warrior_attack_power():
    cfg = class_config("warrior")
    assert STATS.off_hand is None and STATS.main_hand[2] >= 3.0
    assert cfg["ap_str"] == 2 and cfg["ap_agi"] == 0


def test_heroic_strike_bonus_comes_from_effect_17():
    assert best_rank(SPELLS, "Heroic Strike", 60).weapon_bonus == 157
    assert best_rank(SPELLS, "Mortal Strike", 60).weapon_normalized


def test_rage_conversion_matches_classic():
    assert rage_conversion(60) == pytest.approx(230.6, abs=0.1)


def test_damage_talents_carry_rules():
    assert REPORT == []
    assert {"Cruelty", "Impale", "Deep Wounds", "Unbridled Wrath", "Two-Handed Weapon Specialization"} <= set(W.TALENT_EFFECTS)
    heroic = CLS.talent_named("Improved Heroic Strike")
    assert heroic.effects[0].values[-1] == -3          # reductions are negative


def test_arms_spends_rage_on_mortal_strike():
    r = warrior_rotation(STATS, SPELLS, CLS, ARMS, BOSS)
    assert r.abilities[0] == "Mortal Strike" and r.dps > r.white_dps > 0
    assert 2 < r.rage_per_second < 10


@pytest.mark.parametrize("talent", ["Cruelty", "Two-Handed Weapon Specialization", "Deep Wounds", "Impale"])
def test_each_damage_talent_raises_dps(talent):
    full = warrior_rotation(STATS, SPELLS, CLS, ARMS, BOSS).dps
    assert warrior_rotation(STATS, SPELLS, CLS, without(ARMS, talent), BOSS).dps < full


def test_mortal_strike_needs_the_talent():
    r = warrior_rotation(STATS, SPELLS, CLS, without(ARMS, "Mortal Strike"), BOSS)
    assert "Mortal Strike" not in r.abilities


def test_warriors_eat_between_pulls():
    # questing downtime is health, as for rogues (not a pet tanking)
    assert questing("warrior", STATS, SPELLS, CLS, ARMS) < 3600 / 20


def test_pvp_side_uses_warrior_controls():
    side = class_side("warrior", STATS, SPELLS, CLS, ARMS)
    assert side.interrupt > 0 and side.stun > 0 and side.slow == 0.5
    assert side.physical_taken < 1                     # plate takes less than cloth


def test_report_scores_arms_and_leaves_protection_unscored():
    r = json.loads((ROOT / "data" / "report-warrior.json").read_text(encoding="utf-8"))
    assert r["engine"] is True and r["caveats"][0].startswith("Warrior model (#162)")
    slots = {(s["archetype"], s["focus"]): s for s in r["shortlist"]}
    assert 0 < slots[("deep Arms", "PvP")]["standard_score"] < 1
    assert all(s["standard_score"] is None and s["model_pick"] is None
               for (a, _), s in slots.items() if a == "deep Protection")
    builds = {b["id"]: b for b in r["builds"]}
    assert builds["warrior-arms"]["scores"] and not builds["warrior-protection"]["scores"]
