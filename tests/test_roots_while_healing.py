"""Roots hold while the side heals instead of attacking (#290).

Since #286 a root on the opponent being damaged holds only threshold / DPS seconds. While the side
heals (the duel's healing branch, #265), nobody is attacked, so roots hold fully. The healing branch's
damage rate becomes the time-weighted mean of the attacking rate and the healing rate:
  mean = (net x T_side + net_heal x heal_time) / (T_side + heal_time).

Duel (BASE_MAGE as in test_duel.py: 3000 health, 150 DPS, root 20, slow 0.5; MELEE 4000 health 200 DPS;
mage uptime 0.5), break share 0.1, root duration 10, healing 2000 at 400/s (5 s):
  attacking: hold 0.266667, kiting 20.333, net 200 x 39.667/60 = 132.222 (score without healing 0.298453)
  healing: full root, kiting 35, net 200 x 25/60 = 83.333
  mean = (132.222 x 53.333 + 83.333 x 5) / 58.333 = 128.031746; T_opp = 5000 / 128.031746 = 39.052814;
  score 39.052814 / (58.333333 + 39.052814) = 0.401010 (before #290: 5000 / 132.222 = 37.815, 0.393)

Outnumbered (SIDE as in test_outnumbered.py: 4000 health, 200 DPS, root 20; A 3000/100; B 2000/150 with a
4 s stun every 20 s), break share 0.1, root duration 10, three root targets, same healing, B first:
  phase 1 attacking: B hold 0.1, 145 + A rooted 66.667 = 211.667; healing: B fully rooted 100 + 66.667 =
  166.667; phase 1 lasts 12.5 + 5 = 17.5 s at (211.667 x 12.5 + 166.667 x 5) / 17.5 = 198.809524:
  3479.167 of 6000, 2520.833 left; phase 2 A (hold 0.15) 95/s: 26.535088; T_die 44.035088, T 32.5,
  score 0.575358 (without healing 0.493128)
"""

import dataclasses

import pytest

from wowforever.pvp.duel import Control, Kit, Side, duel, outnumbered

BASE_MAGE = Side(health=3000, dps=150, absorb_per_min=0, immunity_share=0,
                     root=20, stun=0, slow=0.5, interrupt=20)
MELEE = Kit(id="test-melee", role="melee", stealth=False, dispels_buffs=False, health=4000, dps=200,
            opener_damage=900, opener_stun=4.0,
            controls=(Control("stun", 3, 30), Control("interrupt", 4, 10), Control("slow", 15, 0)),
            removes=(), immunity=None)
A = Kit(id="a", role="melee", stealth=False, dispels_buffs=False, health=3000, dps=100, opener_damage=0,
        opener_stun=0, controls=(), removes=(), immunity=None)
B = Kit(id="b", role="melee", stealth=False, dispels_buffs=False, health=2000, dps=150, opener_damage=0,
        opener_stun=0, controls=(Control("stun", 4, 20),), removes=(), immunity=None)
SIDE = Side(health=4000, dps=200, absorb_per_min=0, immunity_share=0, root=20, stun=0, slow=0, interrupt=0)
BREAKS = dict(root_break_health=0.1, root_duration=10, heal_hps=400, heal_budget=2000)


def test_duel_roots_hold_while_healing():
    r = duel(dataclasses.replace(BASE_MAGE, **BREAKS), MELEE, "mage_sees")
    assert (r.t_side, r.t_opponent) == (pytest.approx(58.333333), pytest.approx(39.052814, rel=1e-6))
    assert r.score == pytest.approx(0.401010, rel=1e-5)


def test_outnumbered_focus_root_holds_while_healing():
    side = dataclasses.replace(SIDE, root_targets=3, **BREAKS)
    r = outnumbered(side, B, A)
    assert (r.t_side, r.t_opponent) == (pytest.approx(32.5), pytest.approx(44.035088, rel=1e-6))
    assert r.score == pytest.approx(0.575358, rel=1e-5)


def test_unbroken_roots_change_nothing():
    # without a break share, the healing rate equals the attacking rate (test_duel / test_outnumbered values)
    healer = dataclasses.replace(SIDE, heal_hps=400, heal_budget=2000)
    assert max(outnumbered(healer, B, A).score, outnumbered(healer, A, B).score) == pytest.approx(0.609023, rel=1e-5)
