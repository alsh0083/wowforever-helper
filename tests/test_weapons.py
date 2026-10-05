"""Weapon damage from the client's ItemDamage tables (#129). Spec: docs/tasks/129-weapon-damage.md.
Fixture: five real Forever weapons (build 1.60.1.70205) and the one-hand, two-hand and ranged tables."""

from pathlib import Path

import pytest

from wowforever.normalize import read_tables
from wowforever.weapons import Weapon, load_weapons

WEAPONS = load_weapons(read_tables(Path(__file__).parent / "fixtures" / "wago-1.60.1.70205-weapons"))


def test_arcanite_reaper_matches_its_classic_tooltip():
    w = WEAPONS[12784]
    assert (w.name, w.kind, w.subclass) == ("Arcanite Reaper", "two_hand", 1)
    assert (w.min_damage, w.max_damage, w.speed) == (153, 256, 3.8)
    assert w.dps == pytest.approx((153 + 256) / 2 / 3.8)


@pytest.mark.parametrize("item_id, kind, subclass, low, high, speed", [
    (12783, "one_hand", 15, 55, 102, 1.9),    # Heartseeker, dagger
    (19542, "one_hand", 15, 49, 91, 1.7),     # Scout's Blade, dagger
    (12795, "main_hand", 13, 35, 66, 1.3),    # Blood Talon, fist weapon
    (16996, "ranged", 2, 55, 103, 2.5),       # Gorewood Bow
])
def test_damage_ranges_follow_the_item_level_tables(item_id, kind, subclass, low, high, speed):
    w = WEAPONS[item_id]
    assert (w.kind, w.subclass, w.min_damage, w.max_damage, w.speed) == (kind, subclass, low, high, speed)


def test_every_fixture_weapon_loads():
    assert set(WEAPONS) == {12784, 12783, 19542, 12795, 16996}
    assert all(isinstance(w, Weapon) and w.min_damage <= w.max_damage for w in WEAPONS.values())


def test_update_checks_cache_the_damage_tables():
    from wowforever.sources.wago import TABLES
    assert {"ItemDamageOneHand", "ItemDamageTwoHand", "ItemDamageRanged"} <= set(TABLES)
