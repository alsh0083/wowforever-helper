"""Rogue and hunter stat tables from real gear (#129, part 2). Spec: docs/tasks/129-melee-stats.md.
Synthetic items and weapons, worked by hand against config/melee.toml and config/stats/<class>_base.csv
(level 60: rogue str 80 agi 130 sta 75, base health 1100; hunter str 57 agi 130 sta 85 int 65,
base health 1100, base mana 800). Crit rating: 14 per 1% at 60."""

import pytest

from wowforever.gear import Item, best_set
from wowforever.melee_stats import MeleeStats, melee_stat_table
from wowforever.weapons import Weapon


def item(item_id, name, slot, stats, armor_type=None, item_level=60, required_level=55, quality=3):
    return Item(item_id, name, item_level, required_level, quality, slot, stats, armor_type=armor_type)


ITEMS = [
    item(1, "Leather Chest", "chest", {"agility": 20, "stamina": 10}, armor_type=2),
    item(2, "Mail Chest", "chest", {"agility": 40}, armor_type=3),
    item(3, "Cloth Gloves", "hands", {"crit_rating": 14}, armor_type=1),
    item(10, "Dagger A", "main_hand", {"agility": 5}),
    item(11, "Sword B", "main_hand", {}),
    item(12, "Axe C", "main_hand", {}),
    item(13, "Bow D", "ranged", {"agility": 3}),
]
WEAPONS = {
    10: Weapon(10, "Dagger A", "one_hand", 15, 50, 90, 1.8),
    11: Weapon(11, "Sword B", "one_hand", 7, 60, 110, 2.6),
    12: Weapon(12, "Axe C", "one_hand", 0, 100, 200, 2.0),
    13: Weapon(13, "Bow D", "ranged", 2, 40, 70, 2.8),
}


def test_rogue_at_60_wears_leather_and_dual_wields_rogue_weapons():
    (row,) = melee_stat_table("rogue", ITEMS, WEAPONS, [60])
    assert isinstance(row, MeleeStats)
    # leather chest (not mail), cloth gloves; dagger main hand (dps 38.9*3 + 5 agi beats the sword);
    # the axe is not a rogue weapon; bow for ranged
    assert (row.main_hand, row.off_hand, row.ranged) == ((50, 90, 1.8), (60, 110, 2.6), (40, 70, 2.8))
    assert (row.strength, row.agility, row.stamina) == (80, 130 + 20 + 5 + 3, 75 + 10)
    assert row.attack_power == pytest.approx(2 * 60 + 80 + 158 - 20)
    assert row.ranged_attack_power == pytest.approx(60 + 158 - 10)
    assert row.crit_pct == pytest.approx(158 / 29 + 1)
    assert row.ranged_crit_pct == pytest.approx(158 / 29 + 1)
    assert row.hit_pct == pytest.approx(0)
    assert row.health == pytest.approx(1100 + 10 * 85) and row.mana == 0


def test_hunter_at_60_wears_mail_and_can_use_axes():
    (row,) = melee_stat_table("hunter", ITEMS, WEAPONS, [60])
    assert (row.main_hand, row.off_hand, row.ranged) == ((100, 200, 2.0), (50, 90, 1.8), (40, 70, 2.8))
    assert row.agility == 130 + 40 + 5 + 3
    assert row.attack_power == pytest.approx(2 * 60 + 57 + 178 - 20)
    assert row.ranged_attack_power == pytest.approx(2 * 60 + 2 * 178 - 10)
    assert row.crit_pct == pytest.approx(178 / 53 + 1)
    assert row.mana == pytest.approx(800 + 15 * 65)


def test_hunters_wear_mail_only_from_40():
    low = [item(i.item_id, i.name, i.slot, i.stats, i.armor_type, item_level=30, required_level=25)
           for i in ITEMS]
    (row,) = melee_stat_table("hunter", low, WEAPONS, [30])
    # level 30 base agility 72; leather chest 20 + dagger 5 + bow 3 (axe main hand has no stats)
    assert row.agility == 72 + 20 + 5 + 3


def test_best_set_can_restrict_armor_types():
    caster = [item(20, "Leather Robe", "chest", {"spell_power": 30}, armor_type=2),
              item(21, "Cloth Robe", "chest", {"spell_power": 20}, armor_type=1),
              item(22, "Silk Cloak", "back", {"spell_power": 5}, armor_type=1)]
    assert best_set(caster, 60, 4)["chest"].name == "Leather Robe"            # no restriction
    chosen = best_set(caster, 60, 4, armor=frozenset({1}))
    assert chosen["chest"].name == "Cloth Robe" and chosen["back"].name == "Silk Cloak"


def test_items_know_their_armor_type():
    from pathlib import Path
    from wowforever.gear import load_items
    from wowforever.normalize import read_tables
    items = load_items(read_tables(Path(__file__).parent / "fixtures" / "wago-1.60.1.70205-items"))
    assert any(i.armor_type == 1 for i in items)          # cloth in the mage fixture
