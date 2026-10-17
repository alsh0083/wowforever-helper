"""Every class's dungeon pull runs on its mana pool (#348; the owner's #317 decision)."""

import pytest

from wowforever.melee_scenarios import Output, dungeon_pull


def test_full_dps_until_the_pool_runs_dry_then_the_fallback():
    out = Output(100.0, 50.0, 40.0)                 # 2000 mana at 50/s lasts 40 s of the 60 s pull
    assert dungeon_pull(out, 2000.0, 60) == pytest.approx((40 * 100 + 20 * 40) / 60)


def test_no_mana_cooldown_between_pulls():
    out = Output(100.0, 50.0, 40.0, mana_cooldown=(6.0, 5000.0))    # Evocation isn't used on a pull
    assert dungeon_pull(out, 2000.0, 60) == pytest.approx(80.0)


def test_no_drain_keeps_full_dps():
    assert dungeon_pull(Output(100.0, 0.0, 100.0), 0.0, 60) == 100.0
    assert dungeon_pull(Output(100.0, 10.0, 0.0), 2000.0, 60) == 100.0      # 2000 mana outlasts the pull


def test_life_tap_fallback_spends_gcds_tapping():
    from wowforever.classes.engines import life_tap_fallback

    tap = {"gcd": 1.5, "ranks": [[6, 20], [56, 420]]}
    # level 60: rank 56 gives 420 + 4 mana per 1.5 s tap
    assert life_tap_fallback(300.0, 50.0, 60, tap) == pytest.approx(300 / (1 + 50 * 1.5 / 424))
    assert life_tap_fallback(300.0, 50.0, 10, tap) == pytest.approx(300 / (1 + 50 * 1.5 / 24))
    assert life_tap_fallback(300.0, 0.0, 60, tap) == 300.0


# unbuffed dungeon DPS at 60 (group.dungeon_dps with no party) on the pinned dataset; regression pins, re-pinned
# when a class's model changes (1.60.1.70425: #353). Warrior and rogue have no mana and don't move
PINS = [("warrior", "warrior-arms", 130.87), ("rogue", "rogue-combat", 230.84),
        ("warlock", "warlock-affliction", 295.28), ("mage", "deep-frost", 366.08), ("mage", "deep-fire", 257.72),
        ("hunter", "hunter-marksmanship", 184.28), ("priest", "priest-discipline-smite", 179.49),
        ("shaman", "shaman-elemental", 259.71)]


@pytest.mark.parametrize("class_name, build_id, expected", PINS)
def test_dungeon_dps_at_60(class_name, build_id, expected):
    from wowforever.group import dungeon_dps
    from test_group import _engine

    stats, cls, ranks = _engine(class_name, build_id)
    assert dungeon_dps(class_name, stats, cls, ranks, {}) == pytest.approx(expected, abs=0.01)
