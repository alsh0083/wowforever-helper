"""Diminishing returns and an energy budget for opponent controls (#121).
Spec: docs/tasks/121-duel-dr.md. Constants: dr_chain 1.75, dr_immune_seconds 15,
max_control_energy_share 0.5, min_uptime 0.2."""

from dataclasses import replace

import pytest

from wowforever.pvp.duel import Control, Kit, MageSide, duel, load_kits, mage_side

MAGE = MageSide(health=3000, dps=150, barrier_per_min=0, immunity_share=0, root=0, stun=0,
                slow=0, interrupt=0)
BASE = Kit(id="t", role="melee", stealth=False, dispels_buffs=False, health=4000, dps=200,
           opener_damage=0, opener_stun=0, controls=(), removes=(), immunity=None)


def cap(d):
    return 60 * 1.75 * d / (1.75 * d + 15)


def test_one_dr_category_is_capped_by_its_longest_control():
    # stuns: Kidney 6/20 -> 18 s/min, Gouge 4/10 -> 24 s/min; raw 42, cap(6) = 60*10.5/25.5
    kit = replace(BASE, controls=(Control("stun", 6, 20), Control("stun", 4, 10)))
    assert duel(MAGE, kit, "mage_sees").mage_uptime == pytest.approx(1 - cap(6) / 60)


def test_categories_cap_separately_and_interrupts_are_not_capped():
    # stun 4/10 -> 24 (cap(4) = 19.09), disorient 10/300 -> 2 (cap(10) higher), kick 5/10 -> 30
    kit = replace(BASE, controls=(Control("stun", 4, 10), Control("disorient", 10, 300),
                                  Control("interrupt", 5, 10)))
    lockout = cap(4) + 2 + 30
    assert duel(MAGE, kit, "mage_sees").mage_uptime == pytest.approx(max(0.2, 1 - lockout / 60))


def test_energy_budget_scales_every_control_before_the_cap():
    # spend: Gouge 45*6 + Kick 25*6 = 420 > 600*0.5 -> f = 300/420
    kit = replace(BASE, energy_per_minute=600,
                  controls=(Control("stun", 4, 10, energy=45), Control("interrupt", 5, 10, energy=25)))
    f = 300 / 420
    lockout = min(24 * f, cap(4)) + 30 * f
    assert duel(MAGE, kit, "mage_sees").mage_uptime == pytest.approx(1 - lockout / 60)


def test_within_budget_controls_are_not_scaled():
    kit = replace(BASE, energy_per_minute=600, controls=(Control("interrupt", 5, 10, energy=25),))
    assert duel(MAGE, kit, "mage_sees").mage_uptime == pytest.approx(1 - 30 / 60)


def test_kits_without_energy_or_dr_kinds_behave_as_before():
    kit = replace(BASE, controls=(Control("interrupt", 4, 10), Control("slow", 15, 0)))
    assert duel(MAGE, kit, "mage_sees").mage_uptime == pytest.approx(1 - 24 / 60)


def test_rogue_kits_carry_energy_and_leave_the_floor():
    kits = {k.id: k for k in load_kits()}
    for kid in ("rogue-combat", "rogue-subtlety"):
        k = kits[kid]
        assert k.energy_per_minute == 600
        assert {c.energy for c in k.controls} >= {25, 45, 125}
        assert duel(MAGE, k, "mage_sees").mage_uptime > 0.2 + 1e-9, kid
