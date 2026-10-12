"""Damage breaks Entangling Roots on the target being damaged (#286).

Forever's Roots text keeps Classic's "Damage caused may interrupt the effect"; Improved Entangling Roots
lets "its victims take up to 25/50/75% more damage without interrupting the effect". No public source
gives the base amount. Assumption `roots_break_health_pct` (default 10: AzerothCore's threshold, 10% of
the rooted target's maximum health; 0 = roots never break, the old model).

A root on a target the side is damaging holds threshold / side DPS seconds of its duration:
  hold = min(1, break share x (1 + talent %) x target health / (side DPS x root duration)),
and the side's root seconds per minute against that target scale by `hold`. A root on an opponent the
side isn't attacking (the outnumbered score's off-target) holds fully. Sides without a break share
(the mage's, for now) keep full roots.

Duel (test_duel.py's BASE_MAGE: 150 DPS, root 20, slow 0.5; MELEE: 4000 health, 200 DPS, mage uptime 0.5),
break share 0.1, root duration 10: hold = 400 / 1500 = 0.266667, root 5.333 s/min; kiting 5.333 + 15 =
20.333, opponent uptime 39.667 / 60; T_opp = 3000 / 132.222 = 22.689076; T_mage = 53.333333;
score 0.298453. Break share 1.0: hold = 4000 / 1500, capped at 1: the unbroken duel.

Outnumbered (test_outnumbered.py's SIDE, 200 DPS, root 20; A 3000 health 100 DPS; B 2000 health 150 DPS),
break share 0.1, root duration 10:
  B first: off-target A fully rooted, phase 1 216.667 x 12.5 = 2708.333, 1291.667 left; phase 2 A
    hold 300 / 2000 = 0.15, root 3, A uptime 57/60, 95/s: 13.596491; T_die 26.096491, T 27.5,
    score 0.486907.
  A first: phase 1 100 + 100 = 200 x 18.75 = 3750, 250 left; phase 2 B hold 200 / 2000 = 0.1, root 2,
    150 x 58/60 = 145/s: 1.724138; T_die 20.474138, T 31.25, score 0.395833.
  Three root targets, B first: focus B hold 0.1, root 2, 145 + A 66.667 = 211.667 x 12.5 = 2645.833,
    1354.167 left / 95 = 14.254386; T_die 26.754386, score 26.754386 / 54.254386 = 0.493128.
"""

import dataclasses

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.classes.druid import TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.pvp.class_pvp import class_side
from wowforever.pvp.duel import Control, Kit, MageSide, duel, outnumbered, root_hold
from wowforever.schema import Dataset, latest_dataset_path

# as in test_duel.py
BASE_MAGE = MageSide(health=3000, dps=150, barrier_per_min=0, immunity_share=0,
                     root=20, stun=0, slow=0.5, interrupt=20)
MELEE = Kit(id="test-melee", role="melee", stealth=False, dispels_buffs=False, health=4000, dps=200,
            opener_damage=900, opener_stun=4.0,
            controls=(Control("stun", 3, 30), Control("interrupt", 4, 10), Control("slow", 15, 0)),
            removes=(), immunity=None)
# as in test_outnumbered.py
A = Kit(id="a", role="melee", stealth=False, dispels_buffs=False, health=3000, dps=100, opener_damage=0,
        opener_stun=0, controls=(), removes=(), immunity=None)
B = Kit(id="b", role="melee", stealth=False, dispels_buffs=False, health=2000, dps=150, opener_damage=0,
        opener_stun=0, controls=(Control("stun", 4, 20),), removes=(), immunity=None)
SIDE = MageSide(health=4000, dps=200, barrier_per_min=0, immunity_share=0, root=20, stun=0, slow=0, interrupt=0)

CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("druid"), TALENT_EFFECTS, UNMODELED)
BUILDS = {b.id: b for b in load_builds(class_name="druid")}


def test_a_damaged_target_breaks_free_after_the_threshold():
    mage = dataclasses.replace(BASE_MAGE, root_break_health=0.1, root_duration=10)
    assert root_hold(mage, MELEE) == pytest.approx(0.266667, rel=1e-5)
    assert duel(mage, MELEE, "mage_sees").score == pytest.approx(0.298453, rel=1e-5)


def test_hold_is_capped_at_the_full_root():
    mage = dataclasses.replace(BASE_MAGE, root_break_health=1.0, root_duration=10)
    assert root_hold(mage, MELEE) == 1.0
    assert duel(mage, MELEE, "mage_sees").score == pytest.approx(duel(BASE_MAGE, MELEE, "mage_sees").score)


def test_sides_without_a_break_share_keep_full_roots():
    assert root_hold(BASE_MAGE, MELEE) == 1.0


def test_outnumbered_off_target_roots_hold_and_the_focus_breaks_free():
    side = dataclasses.replace(SIDE, root_break_health=0.1, root_duration=10)
    assert outnumbered(side, B, A).score == pytest.approx(0.486907, rel=1e-5)
    assert outnumbered(side, A, B).score == pytest.approx(0.395833, rel=1e-5)
    assert outnumbered(dataclasses.replace(side, root_targets=3), B, A).score == pytest.approx(0.493128, rel=1e-5)


def test_improved_entangling_roots_raises_the_threshold():
    assert PROBLEMS == []
    effects = [(e.kind, e.values, e.applies_to)
               for e in next(t for t in CLS.talents if t.name == "Improved Entangling Roots").effects]
    assert effects == [("break_threshold_pct", (25.0, 50.0, 75.0), ("Entangling Roots",))]
    stats = stat_table("druid").at(60)
    ranks = BUILDS["druid-balance-pvp-leveling"].final_ids(CLS)   # Improved Entangling Roots 3/3
    side = class_side("druid", stats, CLS.spells, CLS, ranks)
    assert (side.root_break_health, side.root_duration) == (pytest.approx(0.175), 10.0)
    talent = next(t.talent_id for t in CLS.talents if t.name == "Improved Entangling Roots")
    assert class_side("druid", stats, CLS.spells, CLS, {**ranks, talent: 0}).root_break_health == pytest.approx(0.1)
    never = Assumptions.load().with_values(roots_break_health_pct=0)
    assert class_side("druid", stats, CLS.spells, CLS, ranks, assumptions=never).root_break_health == 0.0
