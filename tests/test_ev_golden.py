"""Golden tests for the expected-value engine (#17), written before the implementation.

Every expected value is worked by hand in the comment beside it, from Classic-era spell rules:
- Spell miss vs target level difference (target - caster): -2..0 -> 2/3/4%, +1 -> 5%, +2 -> 6%,
  +3 -> 17%, then +11% per further level. Gear/talent hit lowers it; floor is 1%.
- Average hit = ((min + max) / 2 + coefficient * spell_power) * (1 + damage_pct / 100).
- Spell crit deals 150%: the crit *bonus* is 50%, and crit_damage_bonus_pct scales that bonus
  (Ice Shards 5/5 = +100% -> crits deal 200%).
- Ignite: fire-school crits add ignite_pct % of the crit's damage over time.
- Periodic damage = (periodic_damage + periodic_coefficient * spell_power) * (1 + damage_pct / 100);
  it lands only if the spell hits and cannot crit unless `periodic_can_crit`.
- Resistances are ignored in v0.
"""

import pytest

from wowforever.calc.ev import Modifiers, casts_to_oom, effective_cast_time, expected_damage, miss_chance
from wowforever.schema import SpellRank

FIRE = SpellRank(1, "Test Fire", 1, 60, ("fire",), 3.5, mana_cost=400,
                 min_damage=100, max_damage=120, coefficient=0.5)
FROST = SpellRank(2, "Test Frost", 1, 60, ("frost",), 3.0, mana_cost=300,
                  min_damage=100, max_damage=120, coefficient=0.5)
DOT = SpellRank(3, "Test Dot", 1, 60, ("fire", "frost"), 3.0, mana_cost=200,
                min_damage=100, max_damage=100, coefficient=0.0,
                periodic_damage=40, periodic_coefficient=0.1, duration=9)


@pytest.mark.parametrize("diff, hit, expected", [
    (0, 0, 4.0), (1, 0, 5.0), (2, 0, 6.0), (3, 0, 17.0), (4, 0, 28.0),
    (-1, 0, 3.0), (-2, 0, 2.0), (-10, 0, 1.0),  # floor
    (3, 3, 14.0),
    (0, 10, 1.0),                               # hit can't push below 1%
])
def test_miss_chance(diff, hit, expected):
    assert miss_chance(60, 60 + diff, hit) == pytest.approx(expected)


def test_plain_hit_with_base_crit():
    # avg = 110 + 0.5*100 = 160; hit 0.96; crit factor 1 + 0.10*0.5 = 1.05
    # 0.96 * 160 * 1.05 = 161.28
    ev = expected_damage(FROST, spell_power=100, crit_pct=10, hit_pct=0,
                         caster_level=60, target_level=60, mods=Modifiers())
    assert ev == pytest.approx(161.28)


def test_fire_vs_boss_with_talents_and_ignite():
    # damage +10%: avg = 160 * 1.1 = 176; crit 10+6 = 16%; miss 17-3 = 14% -> hit 0.86
    # direct: 0.86 * 176 * (1 + 0.16*0.5) = 0.86 * 176 * 1.08 = 163.4688
    # ignite: 0.86 * 0.16 * (176*1.5) * 0.40 = 0.1376 * 264 * 0.4 = 36.3264 * 0.4 = 14.53056
    # total 177.99936  (Ignite uses the already-modified crit; no second damage_pct multiply,
    # matching Forever's 2026-09-24 "Ignite no longer double dips" change)
    mods = Modifiers(damage_pct=10, crit_chance_bonus=6, ignite_pct=40)
    ev = expected_damage(FIRE, spell_power=100, crit_pct=10, hit_pct=3,
                         caster_level=60, target_level=63, mods=mods)
    assert ev == pytest.approx(177.99936)


def test_ignite_ignored_for_non_fire_spells():
    # same as the plain-hit test: Ignite only applies to fire-school spells
    ev = expected_damage(FROST, spell_power=100, crit_pct=10, hit_pct=0,
                         caster_level=60, target_level=60, mods=Modifiers(ignite_pct=40))
    assert ev == pytest.approx(161.28)


def test_ice_shards_doubles_crit_bonus():
    # crit bonus 50% * (1 + 100/100) = 100% -> crit factor 1 + 0.20*1.0 = 1.2
    # 0.96 * 160 * 1.2 = 184.32
    ev = expected_damage(FROST, spell_power=100, crit_pct=20, hit_pct=0,
                         caster_level=60, target_level=60, mods=Modifiers(crit_damage_bonus_pct=100))
    assert ev == pytest.approx(184.32)


def test_periodic_damage_does_not_crit_by_default():
    # direct avg 100, crit 10%: 0.96 * 100 * 1.05 = 100.8
    # periodic 40 + 0.1*100 = 50, no crit: 0.96 * 50 = 48
    # ignite (fire school present): 0.96 * 0.10 * 150 * 0.0 = 0 (ignite_pct 0 here)
    # total 148.8
    ev = expected_damage(DOT, spell_power=100, crit_pct=10, hit_pct=0,
                         caster_level=60, target_level=60, mods=Modifiers())
    assert ev == pytest.approx(148.8)


def test_periodic_can_crit_toggle():
    # periodic 0.96 * 50 * 1.05 = 50.4; total 100.8 + 50.4 = 151.2
    ev = expected_damage(DOT, spell_power=100, crit_pct=10, hit_pct=0,
                         caster_level=60, target_level=60, mods=Modifiers(), periodic_can_crit=True)
    assert ev == pytest.approx(151.2)


def test_cast_time_reduction_and_gcd_floor():
    assert effective_cast_time(FIRE, Modifiers(cast_time_delta=-0.5)) == pytest.approx(3.0)
    instant = SpellRank(4, "Instant", 1, 60, ("fire",), 0.0)
    assert effective_cast_time(instant, Modifiers()) == pytest.approx(1.5)  # global cooldown


def test_casts_to_oom_with_cost_reduction():
    # cost 400 * (1 - 10/100) = 360; floor(3600 / 360) = 10
    assert casts_to_oom(FIRE, mana=3600, mods=Modifiers(mana_cost_pct=-10)) == 10
    # cost 400; floor(3999 / 400) = 9
    assert casts_to_oom(FIRE, mana=3999, mods=Modifiers()) == 9
