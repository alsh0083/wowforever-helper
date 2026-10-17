"""Longer DoTs and Life Tap (#384 part 2, #396): Improved Shadow Word: Pain and Call of Flame add seconds (more
ticks, so more periodic damage and coefficient); Improved Life Tap gives 20% more mana per tap."""

import pytest

from wowforever.caster import caster_rotation, life_tap_pct, longer_dot
from wowforever.classes import class_module
from wowforever.classes.engines import life_tap_fallback
from wowforever.effects import attach_effects
from wowforever.gear import caster_config
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

DS = Dataset.load(latest_dataset_path())


def loaded(name):
    m = class_module(name)
    return attach_effects(DS.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)


def only(cls, name):
    t = cls.talent_named(name)
    return {t.talent_id: t.max_rank}


@pytest.mark.parametrize("name", ["priest", "shaman", "warlock"])
def test_rules_parse(name):
    assert loaded(name)[1] == []


def test_improved_shadow_word_pain():
    cls, _ = loaded("priest")
    swp = best_rank(cls.spells, "Shadow Word: Pain", 60)            # 762 over 18 s, coefficient 1.2
    longer = longer_dot(swp, cls, only(cls, "Improved Shadow Word: Pain"))
    assert longer.duration == 24.0 and longer.tick_period == swp.tick_period
    assert longer.periodic_damage == pytest.approx(762 * 24 / 18)
    assert longer.periodic_coefficient == pytest.approx(swp.periodic_coefficient * 24 / 18)
    assert longer_dot(swp, cls, {}) == swp


def test_call_of_flame_lengthens_flame_shock():
    cls, _ = loaded("shaman")
    shock = best_rank(cls.spells, "Flame Shock", 60)                # 176 over 12 s
    longer = longer_dot(shock, cls, only(cls, "Call of Flame"))
    assert longer.duration == 21.0 and longer.periodic_damage == pytest.approx(176 * 21 / 12)
    assert longer.min_damage == shock.min_damage                    # the direct hit is unchanged


def test_life_tap_fallback_with_improved_life_tap():
    tap = caster_config("warlock")["life_tap"]
    # rank (56, 420) at 60: 424 mana per tap; one 1.5 s GCD per tap; 20% more mana with the talent
    assert life_tap_fallback(100.0, 10.0, 60, tap) == pytest.approx(100 / (1 + 10 * 1.5 / 424))
    assert life_tap_fallback(100.0, 10.0, 60, tap, bonus_pct=20.0) == pytest.approx(100 / (1 + 10 * 1.5 / 508.8))


def test_improved_life_tap_raises_steady_regen():
    cls, _ = loaded("warlock")
    ranks = only(cls, "Improved Life Tap")
    assert life_tap_pct(cls, ranks) == 20
    stats = stat_table("warlock").at(60)
    base = caster_rotation("warlock", stats, cls.spells, cls, {}, Target(3, 0))
    tapped = caster_rotation("warlock", stats, cls.spells, cls, ranks, Target(3, 0))
    # config extra_regen_per_second (Life Tap) 15 mana/s, 20% more
    assert tapped.regen_per_second - base.regen_per_second == pytest.approx(15 * 0.20)
