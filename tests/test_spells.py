"""Tests for mage trainable spell ranks (#10) on real fixtures (build 1.60.1.70205, mage skill lines).

Golden values come straight from the fixture rows; two are cross-checked against independent
sources: Fireball rank 1 deals 14-22 (Classic, unchanged) and max-rank Blizzard deals 1168 total
(Forever spellbook comparison, down from Classic's 1192).
"""

from pathlib import Path

import pytest

from wowforever.normalize_spells import class_spells, ranks_of
from wowforever.normalize import read_tables

TABLES = read_tables(Path(__file__).parent / "fixtures" / "wago-1.60.1.70205-spells")
SPELLS = class_spells(TABLES, skill_lines=(6, 8, 237))


def rank(name, n):
    return ranks_of(SPELLS, name)[n - 1]


def test_rank_numbering_by_level_then_spell_id():
    fireball = ranks_of(SPELLS, "Fireball")
    assert [s.level for s in fireball] == [1, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 60]
    assert [s.rank for s in fireball] == list(range(1, 13))
    assert (fireball[10].spell_id, fireball[11].spell_id) == (10151, 25306)


def test_fireball_rank_1():
    s = rank("Fireball", 1)
    assert (s.spell_id, s.level, s.schools, s.mana_cost) == (133, 1, ("fire",), 30)
    assert (s.min_damage, s.max_damage) == pytest.approx((14.0, 22.0))
    assert s.coefficient == pytest.approx(0.429, abs=1e-3)
    assert s.cast_time == pytest.approx(1.5)
    # burn: 1 damage every 2 s for 4 s
    assert (s.periodic_damage, s.tick_period, s.duration) == pytest.approx((2.0, 2.0, 4.0))
    assert (s.damage_per_level, s.scaling_max_level) == (pytest.approx(0.6), 5)


def test_frostbolt_max_rank():
    s = rank("Frostbolt", 11)
    assert (s.spell_id, s.level, s.schools) == (25304, 60, ("frost",))
    assert (s.min_damage, s.max_damage) == pytest.approx((457.24, 492.76), abs=0.01)
    assert s.coefficient == pytest.approx(0.814, abs=1e-3)
    assert (s.cast_time, s.duration, s.slow_pct) == pytest.approx((3.0, 9.0, 40.0))


def test_frostfire_bolt_is_dual_school_with_dot_and_slow():
    s = rank("Frostfire Bolt", 1)
    assert (s.spell_id, s.level, s.schools, s.mana_cost) == (401502, 40, ("fire", "frost"), 205)
    assert (s.min_damage, s.max_damage) == pytest.approx((92.33, 107.67), abs=0.01)
    assert (s.cast_time, s.range, s.slow_pct) == pytest.approx((3.0, 35.0, 40.0))
    # 9 every 3 s for 9 s
    assert (s.periodic_damage, s.tick_period, s.duration) == pytest.approx((27.0, 3.0, 9.0))
    assert [r.level for r in ranks_of(SPELLS, "Frostfire Bolt")] == [40, 50, 60]


def test_blizzard_damage_comes_from_area_trigger_tick_spells():
    top = rank("Blizzard", 6)
    assert (top.spell_id, top.level, top.mana_cost, top.schools) == (10187, 60, 1400, ("frost",))
    assert (top.min_damage, top.max_damage) == (0.0, 0.0)
    # 146 per tick, 1 tick/s for 8 s = 1168 (Forever; Classic was 1192)
    assert (top.periodic_damage, top.tick_period, top.duration) == pytest.approx((1168.0, 1.0, 8.0))
    assert top.periodic_coefficient == pytest.approx(0.042 * 8, abs=1e-3)
    assert top.max_targets == 0
    assert rank("Blizzard", 1).periodic_damage == pytest.approx(24 * 8)


def test_flamestrike_direct_plus_area_burn():
    s = rank("Flamestrike", 1)
    assert (s.spell_id, s.level) == (2120, 16)
    assert (s.min_damage, s.max_damage) == pytest.approx((52.0, 68.0), abs=0.01)
    assert s.coefficient == pytest.approx(0.157, abs=1e-3)
    # 11 every 2 s for 8 s
    assert (s.periodic_damage, s.tick_period) == pytest.approx((44.0, 2.0))
    assert s.periodic_coefficient == pytest.approx(0.032 * 4, abs=1e-3)


def test_cooldowns_take_the_longer_of_spell_and_category_recovery():
    assert rank("Ice Block", 1).cooldown == pytest.approx(300.0)
    assert rank("Cold Snap", 1).cooldown == pytest.approx(600.0)
    assert rank("Cone of Cold", 1).cooldown == pytest.approx(10.0)
    assert rank("Fire Blast", 1).cooldown == pytest.approx(8.0)


def test_rune_spells_and_npc_versions_are_excluded():
    names = {s.name for s in SPELLS}
    assert "Living Bomb" not in names and "Arcane Surge" not in names   # SoD runes (AcquireMethod 3)
    assert all(s.level >= 1 for s in SPELLS)
    assert len(ranks_of(SPELLS, "Flamestrike")) == 6


def test_ice_lance_is_trainable_from_20_in_forever():
    assert [s.level for s in ranks_of(SPELLS, "Ice Lance")] == [20, 28, 34, 42, 48, 56]
