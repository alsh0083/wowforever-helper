import pytest

from wowforever.assumptions import Assumptions, impact_rolls_per_cast, periodic_can_crit
from wowforever.calc.ev import Modifiers, expected_damage
from wowforever.schema import SpellRank

A = Assumptions.load()
FFB = SpellRank(401502, "Frostfire Bolt", 1, 40, ("fire", "frost"), 3.0, mana_cost=205,
                min_damage=100, max_damage=100, coefficient=0.0, periodic_damage=27, duration=9)


def test_shipped_config_loads_and_defaults_are_valid():
    assert set(A.describe()) >= {"frostfire_periodic_can_crit", "frostfire_ticks_trigger_impact",
                                 "burning_soul_protects_frostfire", "frostfire_interrupt_lockout",
                                 "fingers_of_frost_applies_to_frostfire", "aoe_target_cap"}
    for entry in A.entries.values():
        assert entry.why and entry.source


def test_with_values_overrides_and_validates():
    assert A.with_values(frostfire_interrupt_lockout="fire")["frostfire_interrupt_lockout"] == "fire"
    assert A["frostfire_interrupt_lockout"] == "both"            # original untouched
    with pytest.raises(ValueError):
        A.with_values(frostfire_interrupt_lockout="arcane")


def test_variants_cover_every_combination():
    combos = {(v["frostfire_ticks_trigger_impact"], v["frostfire_interrupt_lockout"])
              for v in A.variants("frostfire_ticks_trigger_impact", "frostfire_interrupt_lockout")}
    assert combos == {(t, s) for t in (True, False) for s in ("both", "fire", "frost")}


def test_impact_rolls_toggle_changes_output():
    on = A.with_values(frostfire_ticks_trigger_impact=True)
    off = A.with_values(frostfire_ticks_trigger_impact=False)
    assert impact_rolls_per_cast("Frostfire Bolt", 3, on) == 4
    assert impact_rolls_per_cast("Frostfire Bolt", 3, off) == 1
    assert impact_rolls_per_cast("Fireball", 2, on) == 1


def test_periodic_crit_toggle_changes_expected_damage():
    def ev(assumptions):
        return expected_damage(FFB, spell_power=0, crit_pct=20, hit_pct=0, caster_level=60,
                               target_level=60, mods=Modifiers(),
                               periodic_can_crit=periodic_can_crit("Frostfire Bolt", assumptions))
    crit = ev(A.with_values(frostfire_periodic_can_crit=True))
    no_crit = ev(A.with_values(frostfire_periodic_can_crit=False))
    # periodic 27 * 0.96 hit * 0.2 crit * 0.5 bonus = 2.592 more with crits
    assert crit - no_crit == pytest.approx(2.592)


def test_sub20_penalty_cuts_the_coefficient_of_low_level_ranks():
    from wowforever.assumptions import sub20_penalized
    from wowforever.schema import SpellRank

    a = Assumptions.load()
    r1 = SpellRank(116, "Frostbolt", 1, 4, ("frost",), 1.5, coefficient=0.407, periodic_coefficient=0.1)
    cut = sub20_penalized(r1, a)                      # 16 levels under 20: x (1 - 0.6) = x 0.4
    assert cut.coefficient == pytest.approx(0.407 * 0.4)
    assert cut.periodic_coefficient == pytest.approx(0.1 * 0.4)
    r5 = SpellRank(8406, "Frostbolt", 5, 26, ("frost",), 3.0, coefficient=0.814)
    assert sub20_penalized(r5, a) == r5               # learned at 20 or later: unchanged
    assert sub20_penalized(r1, a.with_values(sub20_spell_penalty=False)) == r1
