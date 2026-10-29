"""Ice Barrier's Frost damage on 1.60.1.70685 (#443).

70685 rank text: "Shield yourself, absorbing 447 damage and increasing your Frost damage by 3% for 1 min. While
shielded, your Frost damage is increased by an additional 3% and you do not lose casting time when you take
damage." The 3% lasts the buff's minute (recast on cooldown: always up). The extra 3% holds only while the shield
holds: a best-effort toggle, `ice_barrier_shield_holds` in config/assumptions.toml, on by default for PvE scoring
(nothing hits the mage on a boss). The GCD of recasting it once a minute isn't charged.
"""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.calc.talents import modifiers_for
from wowforever.classes import class_module
from wowforever.classes.mage_rotation import rotation
from wowforever.effects import attach_effects
from wowforever.scenarios import Character, best_rank
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.stats import Stats

M = class_module("mage")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("mage"), M.TALENT_EFFECTS,
                               M.UNMODELED)
IB = CLS.talent_named("Ice Barrier").talent_id
STATS = Stats(60, intellect=270, spirit=190, stamina=220, spell_power=150, crit_pct=6, hit_pct=3,
              mana=3600, health=2900)
A = Assumptions.load().with_values(level_resistance=False)


def spell(name):
    return best_rank(CLS.spells, name, 60)


def test_ice_barrier_rules_parse():
    assert not [p for p in PROBLEMS if "Ice Barrier" in p]
    effects = [(e.kind, tuple(e.values), tuple(e.applies_to)) for e in CLS.talent_named("Ice Barrier").effects]
    assert effects == [("damage_pct", (3.0,), ("frost",)), ("damage_pct", (3.0,), ("frost", "@shielded"))]


def test_frost_damage_bonus_with_and_without_the_shield():
    frostbolt, fireball = spell("Frostbolt"), spell("Fireball")
    assert modifiers_for(frostbolt, CLS, {IB: 1}, frozenset()).damage_pct == pytest.approx(3.0)
    assert modifiers_for(frostbolt, CLS, {IB: 1}, frozenset({"shielded"})).damage_pct == pytest.approx(6.0)
    assert modifiers_for(fireball, CLS, {IB: 1}, frozenset({"shielded"})).damage_pct == pytest.approx(0.0)


def test_the_assumption_defaults_on_and_the_rotation_reads_it():
    assert Assumptions.load()["ice_barrier_shield_holds"] is True

    def dps(ranks, assumptions):
        return rotation(Character(60, STATS, CLS.spells, CLS, ranks), spell("Frostbolt"), target_level=63,
                        assumptions=assumptions, sustained=True).dps

    base = dps({}, A)
    # Frostbolt with no other talents: damage x 1.06 with the shield held, x 1.03 without
    assert dps({IB: 1}, A) / base == pytest.approx(1.06)
    assert dps({IB: 1}, A.with_values(ice_barrier_shield_holds=False)) / base == pytest.approx(1.03)
