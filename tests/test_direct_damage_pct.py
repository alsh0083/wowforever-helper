"""Direct-only damage bonus (#384, Aftermath): `Modifiers.direct_damage_pct` raises a spell's initial hit (and the
Ignite that its crits feed), not its periodic damage. Talent effect kind `direct_damage_pct` maps to it."""

import pytest

from wowforever.calc.ev import Modifiers, expected_damage
from wowforever.calc.talents import modifiers_for
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, SpellRank, latest_dataset_path

DOT = SpellRank(3, "Test Dot", 1, 60, ("fire", "frost"), 3.0, mana_cost=200,
                min_damage=100, max_damage=100, coefficient=0.0,
                periodic_damage=40, periodic_coefficient=0.1, duration=9)


def ev(mods):
    return expected_damage(DOT, spell_power=100, crit_pct=10, hit_pct=0, caster_level=60, target_level=60,
                           mods=mods)


def test_by_hand():
    # direct: 100 x 1.5 = 150; hit 0.96, crit factor 1.05 -> 151.2. periodic: (40 + 0.1 x 100) = 50 x 0.96 = 48.
    # base: 100 x 0.96 x 1.05 = 100.8 + 48 = 148.8; with +50% direct: 151.2 + 48 = 199.2
    assert ev(Modifiers()) == pytest.approx(148.8)
    assert ev(Modifiers(direct_damage_pct=50)) == pytest.approx(199.2)
    # it stacks with damage_pct on the direct part: 100 x 1.1 x 1.5 = 165 x 1.008 = 166.32; periodic 55 x 0.96 = 52.8
    assert ev(Modifiers(damage_pct=10, direct_damage_pct=50)) == pytest.approx(166.32 + 52.8)


def test_ignite_follows_the_direct_hit():
    # ignite 40%: hit 0.96 x crit 0.1 x (direct avg x 1.5) x 0.4; direct avg 150 with the bonus, 100 without
    with_bonus = ev(Modifiers(direct_damage_pct=50, ignite_pct=40)) - ev(Modifiers(direct_damage_pct=50))
    assert with_bonus == pytest.approx(0.96 * 0.1 * 150 * 1.5 * 0.4)


def test_aftermath():
    w = class_module("warlock")
    cls, problems = attach_effects(Dataset.load(latest_dataset_path()).class_data("warlock"), w.TALENT_EFFECTS,
                                   w.UNMODELED)
    assert problems == []
    (rule,) = cls.talent_named("Aftermath").effects
    assert (rule.kind, rule.applies_to, rule.values) == ("direct_damage_pct", ("Immolate",),
                                                         (10.0, 20.0, 30.0, 40.0, 50.0))
    immolate = best_rank(cls.spells, "Immolate", 60)
    ranks = {cls.talent_named("Aftermath").talent_id: 5}
    assert modifiers_for(immolate, cls, ranks).direct_damage_pct == 50.0
