"""Multi-target controls when outnumbered (#287).

In the 2v1 score (#278) the defender's single-target stuns, slows and interrupts are split between the two
opponents (outnumbered_control_split 0.5). Controls whose spell hits several enemies reach both in full:
- class_side: `stun_aoe` = the stun/fear lockout of the controls whose data MaxTargets > 1 (Psychic Scream,
  Intimidating Shout: 5), capped at the side's whole stun. Shadow priest: Psychic Scream 8 s every 30 s =
  16 s/min. Arms warrior: Intimidating Shout 8 s every 180 s = 2.667 s/min.
- outnumbered: phase-1 stun = (stun - stun_aoe) x 0.5 + stun_aoe for each opponent.
- mage_side: Frost Nova roots every nearby enemy, so a mage that knows it has root_targets 2.

Hand-worked (test_outnumbered.py's SIDE: 4000 health, 200 DPS, root 20; A 3000/100; B 2000/150 with a
4 s stun every 20 s), stun 10 all from multi-target controls, slow 0.2, A first:
  A: root 0 + stun 10 + slow 0.1 x 30 = 13 s/min, 100 x 47/60 = 78.333; B: 20 + 10 + 3 = 33, 150 x 27/60 = 67.5;
  phase 1 145.833 x 18.75 = 2734.375, 1265.625 left; phase 2 B: 20 + 10 + 6 = 36, 60/s: 21.09375;
  T_die 39.84375, T 31.25, score 0.560440 (split stuns: 0.516129).
"""

import dataclasses

import pytest

from wowforever import melee_scenarios as ms
from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.pvp.class_pvp import class_side
from wowforever.classes.mage import duel_side
from wowforever.pvp.duel import Control, Kit, Side, outnumbered
from wowforever.report import ranks_at
from wowforever.scenarios import Character, best_rank
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.stats import StatTable

DATASET = Dataset.load(latest_dataset_path())
A = Kit(id="a", role="melee", stealth=False, dispels_buffs=False, health=3000, dps=100, opener_damage=0,
        opener_stun=0, controls=(), removes=(), immunity=None)
B = Kit(id="b", role="melee", stealth=False, dispels_buffs=False, health=2000, dps=150, opener_damage=0,
        opener_stun=0, controls=(Control("stun", 4, 20),), removes=(), immunity=None)
SIDE = Side(health=4000, dps=200, absorb_per_min=0, immunity_share=0, root=20, stun=0, slow=0, interrupt=0)


def test_multi_target_stuns_reach_both_opponents():
    wide = dataclasses.replace(SIDE, stun=10, stun_aoe=10, slow=0.2)
    assert outnumbered(wide, A, B).score == pytest.approx(0.560440, rel=1e-5)
    assert outnumbered(dataclasses.replace(wide, stun_aoe=0), A, B).score == pytest.approx(0.516129, rel=1e-5)


def side(class_name, build_id):
    module = class_module(class_name)
    cls, _ = attach_effects(DATASET.class_data(class_name), module.TALENT_EFFECTS, module.UNMODELED)
    ranks = {b.id: b for b in load_builds(class_name=class_name)}[build_id].final_ids(cls)
    return class_side(class_name, ms.stat_table(class_name).at(60), cls.spells, cls, ranks)


def test_class_sides_mark_their_multi_target_controls():
    priest = side("priest", "priest-shadow")
    assert priest.stun_aoe == pytest.approx(16.0) and priest.stun_aoe <= priest.stun
    assert side("warrior", "warrior-arms").stun_aoe == pytest.approx(8 * 60 / 180)
    assert side("rogue", "rogue-combat").stun_aoe == 0


def test_frost_nova_roots_both_opponents():
    module = class_module("mage")
    cls, _ = attach_effects(DATASET.class_data("mage"), module.TALENT_EFFECTS, module.UNMODELED)
    build = next(b for b in load_builds(class_name="mage") if b.order)
    char = Character(60, StatTable.load("mage").at(60), cls.spells, cls, ranks_at(build.order_ids(cls), 60, cls))
    filler = best_rank(cls.spells, "Frostbolt", 60)
    assert duel_side(char, filler).root_targets == 2
