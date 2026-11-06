"""Blood Frenzy's Cat Form part (#397). Berserk was removed in 1.60.1.70755 (#455, #463); its averaged crit window in
druid_rotation and config/druid.toml [berserk] no longer apply to any build.

Blood Frenzy: a non-periodic crit of a combo-point builder adds a combo point (50% / 100% chance), as the rogue's
Seal Fate: combo points per builder = land x (1 + crit x chance)."""

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
BF = CLS.talent_named("Blood Frenzy").talent_id


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
