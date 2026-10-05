"""Tests for placeholder stats from real Forever gear (#68), on the trimmed item fixture.

Stat budget (verified against Classic values): stat = round(RandPropPoints[ilvl].<Quality>_<cat> *
StatPercentEditor / 10000). Robe of the Archmage (ilvl 62 epic robe, budget 45): Int 12, SP 40,
crit rating 14 (= Classic's +1% spell crit).
"""

from pathlib import Path

import pytest

from wowforever.gear import (
    SLOTS, best_set, crit_pct_from_rating, gear_stat_table, item_by_name, load_items, set_totals,
)
from wowforever.normalize import read_tables

ITEMS = load_items(read_tables(Path(__file__).parent / "fixtures" / "wago-1.60.1.70205-items"))


def test_stat_budget_reproduces_known_items():
    robe = item_by_name(ITEMS, "Robe of the Archmage")
    assert (robe.item_level, robe.required_level, robe.quality, robe.slot) == (62, 57, 4, "chest")
    assert robe.stats == {"intellect": 12, "spell_power": 40, "crit_rating": 14}
    circlet = item_by_name(ITEMS, "Dreamweave Circlet")
    assert circlet.stats["spell_power"] == 21 and circlet.slot == "head"


def test_rating_conversion():
    # 14 crit rating = 1% at 60 (the robe); lower levels scale by (level - 8) / 52 (TBC-style, inference)
    assert crit_pct_from_rating(14, 60) == pytest.approx(1.0)
    assert crit_pct_from_rating(14, 34) == pytest.approx(52 / 26)


def test_best_set_respects_level_quality_and_slots():
    s = best_set(ITEMS, level=40, max_quality=3)
    assert set(s) <= set(SLOTS)
    for slot, item in s.items():
        assert item.required_level <= 40 and item.quality <= 3
    rings = [i for k, i in s.items() if k.startswith("finger")]
    assert len({i.item_id for i in rings}) == len(rings)          # two different rings
    assert not ("main_hand" in s and "two_hand" in s)


def test_best_set_prefers_more_weighted_stats():
    s = best_set(ITEMS, level=60, max_quality=4)
    chest = s["chest"]
    # among level-60 chests, nothing has more weighted value than the chosen one
    from wowforever.gear import WEIGHTS, weighted
    rivals = [i for i in ITEMS if i.slot == "chest" and i.required_level <= 60 and i.quality <= 4]
    assert weighted(chest, WEIGHTS) == max(weighted(i, WEIGHTS) for i in rivals)


def test_totals_and_stat_table_are_monotonic_by_level():
    t20, t60 = set_totals(best_set(ITEMS, 20, 3)), set_totals(best_set(ITEMS, 60, 3))
    assert 0 <= t20["spell_power"] < t60["spell_power"] and t20["intellect"] < t60["intellect"]
    rows = gear_stat_table(ITEMS, levels=(20, 30, 40, 50, 60))
    assert [r.level for r in rows] == [20, 30, 40, 50, 60]
    for a, b in zip(rows, rows[1:]):
        assert b.spell_power >= a.spell_power and b.mana >= a.mana and b.health >= a.health
