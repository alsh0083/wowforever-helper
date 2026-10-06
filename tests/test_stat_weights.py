"""Stat weights per build and level from the class's engine (#189)."""

import json
from pathlib import Path

import pytest

from wowforever.gear import MANA_PER_INT, crit_pct_from_rating
from wowforever.melee_scenarios import stat_table
from wowforever.stat_weights import STATS, apply, weights_at
from wowforever.stats import StatTable

ROOT = Path(__file__).resolve().parents[1]


def test_intellect_carries_mana_and_spell_crit_for_casters():
    s = StatTable.load("mage").at(40)
    up = apply("mage", s, "intellect", 10)
    assert up.mana == pytest.approx(s.mana + 10 * MANA_PER_INT) and up.crit_pct > s.crit_pct
    assert apply("mage", s, "strength", 10) is None


def test_melee_rules_turn_strength_agility_and_weapon_dps_into_the_class_stats():
    s = stat_table("warrior").at(60)
    assert apply("warrior", s, "strength", 10).attack_power == pytest.approx(s.attack_power + 20)   # ap_str 2
    agi = apply("rogue", stat_table("rogue").at(60), "agility", 10)
    assert agi.crit_pct > stat_table("rogue").at(60).crit_pct
    lo, hi, speed = s.main_hand
    assert apply("warrior", s, "weapon_dps", 2).main_hand == pytest.approx((lo + 2 * speed, hi + 2 * speed, speed))


def test_hybrids_change_the_row_the_build_fights_with():
    s = stat_table("druid").at(60)
    cat = apply("druid", s, "agility", 10, melee_build=True)
    assert cat.melee.agility == s.melee.agility + 10 and cat.caster == s.caster


def test_weights_are_score_change_per_point():
    s = StatTable.load("mage").at(60)
    w = weights_at("mage", s, lambda st: st.spell_power * 2 + st.crit_pct)
    assert w["spell_power"] == pytest.approx(2) and w["crit_pct"] == pytest.approx(1)
    assert w["crit_rating"] == pytest.approx(crit_pct_from_rating(1, 60), rel=1e-4)   # stored to 6 decimals


def test_reports_carry_weights_for_scored_builds_and_generic_ones_otherwise():
    for path in sorted((ROOT / "data").glob("report*.json")):
        for b in json.loads(path.read_text(encoding="utf-8"))["builds"]:
            w = b["stat_weights"]
            if b.get("scores"):
                assert set(w) == {"20", "30", "40", "50", "60"}, (path.name, b["id"])
                assert set(w["60"]) <= {"score", *STATS}
            else:
                assert set(w) == {"generic"} and w["generic"], (path.name, b["id"])
