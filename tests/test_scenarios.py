"""Golden tests for the v0 PvE scenarios (#19), on tiny synthetic inputs worked by hand.

Shared setup: no talents, 0 spell power, 0 crit, 0 gear hit, so every hit lands for exactly its
damage and only the miss table matters (same level: 4% miss -> 0.96 hit; +3 levels: 17% miss).
"""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.scenarios import (
    AoeParams, Character, QuestingParams, RaidParams, aoe_curve, best_rank, questing, raid, scaled,
)
from wowforever.schema import ClassData, SpellRank
from wowforever.stats import Stats

EMPTY = ClassData("testclass", (), ())
A = Assumptions.load()


def stats(level, mana):
    return Stats(level, 0, 0, 0, spell_power=0, crit_pct=0, hit_pct=0, mana=mana, health=1000)


BOLT = SpellRank(1, "Frostbolt", 1, 20, ("frost",), 2.0, mana_cost=50, min_damage=100, max_damage=100)
BLAST = SpellRank(2, "Arcane Explosion", 1, 20, ("arcane",), 0.0, mana_cost=100, min_damage=50, max_damage=50)
NUKE = SpellRank(3, "Fireball", 1, 60, ("fire",), 2.5, mana_cost=400, min_damage=1000, max_damage=1000)
CHAR20 = Character(level=20, stats=stats(20, 1000), spells=(BOLT, BLAST), cls=EMPTY, ranks={})
CHAR60 = Character(level=60, stats=stats(60, 4000), spells=(NUKE,), cls=EMPTY, ranks={})


def test_scaled_applies_per_level_damage_up_to_the_cap():
    fb = SpellRank(133, "Fireball", 1, 1, ("fire",), 1.5, min_damage=14, max_damage=22,
                   damage_per_level=0.6, scaling_max_level=5)
    assert (scaled(fb, 3).min_damage, scaled(fb, 3).max_damage) == pytest.approx((15.2, 23.2))  # +2 levels
    assert scaled(fb, 30).min_damage == pytest.approx(14 + 0.6 * 4)                           # capped at 5
    assert scaled(BOLT, 60) == BOLT                                                           # no scaling


def test_best_rank_picks_highest_rank_learned_by_level():
    r1 = SpellRank(10, "Frostbolt", 1, 4, ("frost",), 1.5)
    r2 = SpellRank(11, "Frostbolt", 2, 8, ("frost",), 1.8)
    assert best_rank((r1, r2), "Frostbolt", 7) == r1
    assert best_rank((r1, r2), "Frostbolt", 8) == r2
    assert best_rank((r1, r2), "Frostbolt", 3) is None


def test_questing_kills_per_hour():
    # EV per cast 0.96 * 100 = 96; DPS 96 / 2.0 = 48; time to kill 300 / 48 = 6.25 s
    # mana per kill = (300 / 96) * 50 = 156.25; drinking at 20 mana/s = 7.8125 s
    # kills/hour = 3600 / (6.25 + 7.8125 + 10 travel) = 149.61...
    p = QuestingParams(mob_hp=300, travel_seconds=10, drink_mana_per_second=20, fillers=("Frostbolt",))
    r = questing(CHAR20, p, A)
    assert r.score == pytest.approx(3600 / 24.0625)
    assert r.unit == "kills/hour"
    assert r.details["spell"] == "Frostbolt"
    assert r.details["time_to_kill"] == pytest.approx(6.25)
    assert r.details["mana_per_kill"] == pytest.approx(156.25)


def test_aoe_curve_break_even_and_soft_cap():
    # single target chain: 6.25 s per mob (from above)
    # AoE: EV per target 0.96 * 50 = 48 per 1.5 s GCD = 32 DPS on each mob; a pack of 300-HP mobs
    # dies together in 300 / 32 = 9.375 s. n=1: 9.375 > 6.25 (single wins); n=2: 9.375 < 12.5.
    p = AoeParams(mob_hp=300, pack_sizes=(1, 2, 3, 4, 5, 6), aoe_spells=("Arcane Explosion",),
                  fillers=("Frostbolt",))
    r = aoe_curve(CHAR20, p, A.with_values(aoe_target_cap="none"))
    assert r.details["break_even"] == 2
    assert r.details["aoe_time"][6] == pytest.approx(9.375)
    assert r.details["single_time"][6] == pytest.approx(37.5)
    assert r.score == 2 and r.unit == "pack size"
    # soft cap at 4: damage worth 4 targets is shared by n > 4: per-mob DPS 32 * 4 / 6
    capped = aoe_curve(CHAR20, p, A.with_values(aoe_target_cap="soft_4"))
    assert capped.details["aoe_time"][6] == pytest.approx(300 / (32 * 4 / 6))
    assert capped.details["aoe_time"][4] == pytest.approx(9.375)


def test_aoe_curve_with_no_break_even():
    p = AoeParams(mob_hp=300, pack_sizes=(1,), aoe_spells=("Arcane Explosion",), fillers=("Frostbolt",))
    r = aoe_curve(CHAR20, p, A)
    assert r.details["break_even"] is None and r.score == 0


def test_raid_sustained_dps_without_regen():
    # +3 levels: miss 17% -> EV 830; DPS 830 / 2.5 = 332; 10 casts to OOM = 25 s of 180 s
    # sustained = 332 * 25 / 180
    r = raid(CHAR60, RaidParams(fight_seconds=180, mana_per_second=0, fillers=("Fireball",)), A)
    assert r.score == pytest.approx(332 * 25 / 180)
    assert r.unit == "dps"
    assert r.details["time_to_oom"] == pytest.approx(25)


def test_raid_sustained_dps_with_regen():
    # drain 400 / 2.5 - 100 = 60 mana/s -> OOM after 4000 / 60 = 66.67 s
    r = raid(CHAR60, RaidParams(fight_seconds=180, mana_per_second=100, fillers=("Fireball",)), A)
    assert r.score == pytest.approx(332 * (4000 / 60) / 180)


def test_raid_extra_mana_extends_time_to_oom():
    # (4000 + 2000) / (400 / 2.5) = 37.5 s
    p = RaidParams(fight_seconds=180, mana_per_second=0, fillers=("Fireball",), extra_mana=2000)
    assert raid(CHAR60, p, A).details["time_to_oom"] == pytest.approx(37.5)


def test_channeled_aoe_occupies_its_duration():
    # 8 s channel dealing 80 per target: 0.96 * 80 / 8 = 9.6 DPS per mob, not 0.96 * 80 / 1.5
    chan = SpellRank(9, "Blizzard", 1, 20, ("frost",), 0.0, mana_cost=100, periodic_damage=80,
                     duration=8.0, tick_period=1.0, channeled=True)
    char = Character(level=20, stats=stats(20, 1000), spells=(BOLT, chan), cls=EMPTY, ranks={})
    p = AoeParams(mob_hp=300, pack_sizes=(1,), aoe_spells=("Blizzard",), fillers=("Frostbolt",))
    assert aoe_curve(char, p, A).details["aoe_time"][1] == pytest.approx(300 / 9.6)


def test_cooldown_limits_how_often_a_spell_repeats():
    # Arcane Explosion with a 10 s cooldown: 48 per mob every 10 s = 4.8 DPS per mob
    slow = SpellRank(2, "Arcane Explosion", 1, 20, ("arcane",), 0.0, cooldown=10.0, mana_cost=100,
                     min_damage=50, max_damage=50)
    char = Character(level=20, stats=stats(20, 1000), spells=(BOLT, slow), cls=EMPTY, ranks={})
    p = AoeParams(mob_hp=300, pack_sizes=(1,), aoe_spells=("Arcane Explosion",), fillers=("Frostbolt",))
    assert aoe_curve(char, p, A).details["aoe_time"][1] == pytest.approx(300 / 4.8)


def test_repeated_dot_only_counts_ticks_before_the_next_cast():
    # 3 s cast, 100 direct + 80 over 8 s: each repeat gains 0.96 * (100 + 80 * 3 / 8) = 124.8
    burn = SpellRank(7, "Flamestrike", 1, 20, ("fire",), 3.0, mana_cost=100, min_damage=100,
                     max_damage=100, periodic_damage=80, duration=8.0, tick_period=2.0)
    char = Character(level=20, stats=stats(20, 1000), spells=(BOLT, burn), cls=EMPTY, ranks={})
    p = AoeParams(mob_hp=300, pack_sizes=(1,), aoe_spells=("Flamestrike",), fillers=("Frostbolt",))
    assert aoe_curve(char, p, A).details["aoe_time"][1] == pytest.approx(300 / (124.8 / 3.0))


def test_raid_never_oom_caps_at_full_dps():
    r = raid(CHAR60, RaidParams(fight_seconds=180, mana_per_second=500, fillers=("Fireball",)), A)
    assert r.score == pytest.approx(332)
    assert r.details["time_to_oom"] is None


def test_results_record_assumptions_used():
    p = QuestingParams(mob_hp=300, travel_seconds=10, drink_mana_per_second=20, fillers=("Frostbolt",))
    r = questing(CHAR20, p, A.with_values(frostfire_periodic_can_crit=False))
    assert r.assumptions["frostfire_periodic_can_crit"] is False


def test_default_params_from_config_scale_with_level():
    from wowforever.scenarios import default_params
    q20, q60 = default_params("questing", 20), default_params("questing", 60)
    assert 0 < q20.mob_hp < q60.mob_hp
    assert q20.fillers == ("Frostbolt", "Fireball", "Frostfire Bolt", "Arcane Missiles")
    a = default_params("aoe", 40)
    assert a.pack_sizes == (1, 2, 3, 4, 5, 6) and "Blizzard" in a.aoe_spells
    assert default_params("raid", 60).fight_seconds == 180
