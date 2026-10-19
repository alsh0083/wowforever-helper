"""Level-based spell resistance (#409, owner decision 2026-10-19: model it, default on).

Classic: a target above the caster's level resists spells as if it had 8 resistance per level of difference; the
average partial resist is resistance / (caster level x 5) x 0.75. At 60 against 63: 24 / 300 x 0.75 = 6%; against
61: 2%. Arcane Subtlety lowers the resistance (8 / 15). Holy damage isn't resisted. Physical damage is untouched."""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.calc.ev import Modifiers, expected_damage, level_resist_pct
from wowforever.calc.talents import modifiers_for
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, SpellRank, latest_dataset_path

DOT = SpellRank(3, "Test Dot", 1, 60, ("fire", "frost"), 3.0, mana_cost=200,
                min_damage=100, max_damage=100, coefficient=0.0,
                periodic_damage=40, periodic_coefficient=0.1, duration=9)
HOLY = SpellRank(4, "Test Holy", 1, 60, ("holy",), 1.5, mana_cost=100, min_damage=100, max_damage=100)


@pytest.mark.parametrize("caster, target, reduction, expected", [
    (60, 63, 0, 6.0),        # 24 / 300 x 0.75
    (60, 61, 0, 2.0),        # 8 / 300 x 0.75
    (60, 60, 0, 0.0),
    (60, 57, 0, 0.0),        # lower-level targets don't resist by level
    (60, 63, 15, 2.25),      # Arcane Subtlety 2/2: 9 / 300 x 0.75
    (60, 61, 15, 0.0),       # can't go below 0
    (30, 33, 0, 12.0),       # 24 / 150 x 0.75
])
def test_level_resist_pct(caster, target, reduction, expected):
    assert level_resist_pct(caster, target, reduction) == pytest.approx(expected)


def ev(spell, target_level, mods=Modifiers(), resist=True):
    return expected_damage(spell, spell_power=100, crit_pct=10, hit_pct=0, caster_level=60, target_level=target_level,
                           mods=mods, level_resistance=resist)


def test_expected_damage_takes_the_average_resist():
    # 60 vs 63 without resist: hit 0.83; direct 100 x 0.83 x 1.05 = 87.15, periodic 50 x 0.83 = 41.5 -> 128.65
    assert ev(DOT, 63, resist=False) == pytest.approx(128.65)
    assert ev(DOT, 63) == pytest.approx(128.65 * 0.94)
    assert ev(DOT, 63, Modifiers(resistance_reduction=15)) == pytest.approx(128.65 * (1 - 0.0225))
    assert ev(DOT, 60) == pytest.approx(ev(DOT, 60, resist=False))
    # the default is off, so existing callers and golden values are unchanged unless they opt in
    assert expected_damage(DOT, spell_power=100, crit_pct=10, hit_pct=0, caster_level=60, target_level=63,
                           mods=Modifiers()) == pytest.approx(128.65)


def test_holy_is_not_resisted():
    assert ev(HOLY, 63) == pytest.approx(ev(HOLY, 63, resist=False))


def test_assumption_and_arcane_subtlety():
    a = Assumptions.load()
    assert a["level_resistance"] is True and a.entries["level_resistance"].options == (False, True)
    m = class_module("mage")
    cls, problems = attach_effects(Dataset.load(latest_dataset_path()).class_data("mage"), m.TALENT_EFFECTS,
                                   m.UNMODELED)
    assert problems == []
    (rule,) = cls.talent_named("Arcane Subtlety").effects
    assert (rule.kind, rule.applies_to, rule.values) == ("resistance_reduction", ("all",), (8.0, 15.0))
    frostbolt = best_rank(cls.spells, "Frostbolt", 60)
    assert modifiers_for(frostbolt, cls, {cls.talent_named("Arcane Subtlety").talent_id: 2}).resistance_reduction == 15
