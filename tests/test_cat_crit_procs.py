"""Blood Frenzy's Cat Form part and Berserk (#397).

Blood Frenzy: a non-periodic crit of a combo-point builder adds a combo point (50% / 100% chance), as the rogue's
Seal Fate: combo points per builder = land x (1 + crit x chance).
Berserk: +100% crit for combo-point builders for 15 s (rank text); its cooldown isn't in the client data, so
config/druid.toml has a best-effort 180 s. Averaged: a share s = 15 / 180 of the builders crit with +100%, so the
builder's damage and combo points are (1 - s) x normal + s x Berserk."""

from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.classes.druid_rotation import cat_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import Attacker, Target, land_chance, yellow_attack, yellow_crit_chance
from wowforever.scenarios import _anchor_at, best_rank
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.toml_cache import load_toml

D = class_module("druid")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("druid"), D.TALENT_EFFECTS,
                               D.UNMODELED)
STATS = MeleeStatTable.load("druid_melee").at(60)
BOSS = Target(3, 3731)
C = load_toml(Path(__file__).resolve().parents[1] / "config" / "druid.toml")
BF, BERSERK = CLS.talent_named("Blood Frenzy").talent_id, CLS.talent_named("Berserk").talent_id


def attacker():
    return Attacker(60, STATS.attack_power, STATS.crit_pct, STATS.hit_pct)


def test_rule_and_config():
    assert PROBLEMS == []
    (rule,) = [e for e in CLS.talent_named("Blood Frenzy").effects if e.kind == "proc_chance"]
    assert (rule.applies_to, rule.values) == (("@builder_crit",), (50.0, 100.0))
    assert C["berserk"] == {"duration": 15.0, "cooldown": 180.0}


def test_blood_frenzy_combo_points():
    a = attacker()
    land, crit = land_chance(a, BOSS), yellow_crit_chance(a, BOSS)
    r = cat_rotation(STATS, CLS.spells, CLS, {BF: 2}, BOSS)
    assert r.builder == "Claw"
    assert r.combo_points_per_builder == pytest.approx(land * (1 + crit * 1.0))
    assert cat_rotation(STATS, CLS.spells, CLS, {}, BOSS).combo_points_per_builder == pytest.approx(land)


def test_berserk_averages_the_crit_window():
    a = attacker()
    s = 15.0 / 180.0
    land = land_chance(a, BOSS)
    normal, berserk = yellow_crit_chance(a, BOSS), yellow_crit_chance(a, BOSS, 100.0)
    r = cat_rotation(STATS, CLS.spells, CLS, {BF: 2, BERSERK: 1}, BOSS)
    expected = (1 - s) * land * (1 + normal) + s * land * (1 + berserk)
    assert r.combo_points_per_builder == pytest.approx(expected)


def test_berserk_raises_the_builder_damage():
    claw = best_rank(CLS.spells, "Claw", 60)
    lo, hi = _anchor_at(C["paws"], 60)
    base = (lo + hi) / 2 + STATS.attack_power / 14 * C["paw_speed"]
    base = base * (claw.weapon_pct / 100 if claw.weapon_pct else 1) + claw.weapon_bonus
    s = 15.0 / 180.0
    ev = (1 - s) * yellow_attack(base, attacker(), BOSS) + s * yellow_attack(base, attacker(), BOSS, crit_bonus=100.0)
    assert cat_rotation(STATS, CLS.spells, CLS, {BERSERK: 1}, BOSS).builder_ev == pytest.approx(ev)
    assert cat_rotation(STATS, CLS.spells, CLS, {}, BOSS).builder_ev == pytest.approx(yellow_attack(base, attacker(),
                                                                                                   BOSS))
