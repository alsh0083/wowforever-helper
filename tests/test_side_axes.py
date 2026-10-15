"""Survival, control and battleground scores for every class (#322): from a duel Side, not a mage build.

Hand-worked golden values (config/pvp_axes.toml references and weights, consensus battleground mids):
- survival: health 4000, absorbs 1000/min -> barrier 0.25 -> min(1, 0.25/0.5) = 0.5 x 0.35 = 0.175;
  immunity 0.02 -> 0.4 x 0.25 = 0.10; pushback 0.5 -> 0.5 x 0.20 = 0.10; escapes 4/min -> 0.5 x 0.20 = 0.10.
  Score 0.475.
- control: slow 0.25 -> 0.5 x 0.35; root 15 s/min -> 0.5 x 0.35; stun 3 -> 0.5 x 0.15; interrupt 10 -> 0.5 x 0.15.
  Score 0.5.
- battleground at 60: kill 125 / 250 = 0.5; endurance 6000 mana / 100 per s = 60 s / 120 = 0.5;
  0.35 x 0.5 + 0.05 x 0.5 + 0.30 x 0.475 + 0.30 x 0.5 = 0.4925.
"""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.calc.pvp_axes import control, side_control, side_survival, survival
from wowforever.classes import class_module, engine
from wowforever.classes.mage import duel_side
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.pvp.battleground import (battleground, best_battleground, best_side_battleground,
                                         side_battleground)
from wowforever.pvp.duel import Side
from wowforever.scenarios import Character, default_params, usable_fillers
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.stats import StatTable

DATASET = Dataset.load(latest_dataset_path())
SIDE = Side(health=4000, dps=125, absorb_per_min=1000, immunity_share=0.02, root=15, stun=3, slow=0.25,
            interrupt=10, pushback=0.5, escapes=4, mana=6000, mana_per_second=100)


def loaded(name):
    m = class_module(name)
    cls, _ = attach_effects(DATASET.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)
    return cls, [b.final_ids(cls) for b in load_builds(class_name=name)]


def test_survival_and_control_from_a_side():
    s = side_survival(SIDE)
    assert s.score == pytest.approx(0.475)
    assert s.components == {"barrier": 0.25, "immunity": 0.02, "pushback": 0.5, "escapes": 4}
    assert side_control(SIDE).score == pytest.approx(0.5)


def test_battleground_from_a_side():
    r = side_battleground(SIDE, 60)
    assert r["components"] == pytest.approx({"kill": 0.5, "endurance": 0.5, "survival": 0.475, "control": 0.5})
    assert r["score"] == pytest.approx(0.4925)


def test_rage_and_energy_never_run_dry():
    rogue = Side(**{**SIDE.__dict__, "mana": 0.0, "mana_per_second": 0.0})
    assert side_battleground(rogue, 60)["components"]["endurance"] == 1.0


def test_a_mage_side_scores_like_the_mage_axes():
    cls, builds = loaded("mage")
    stats, a = StatTable.load("mage").at(60), Assumptions.load()
    for ranks in builds[:6]:
        char = Character(60, stats, cls.spells, cls, dict(ranks))
        fillers = usable_fillers(char, default_params("questing", 60).fillers, 60, a)
        for f in fillers:
            side = duel_side(char, f)
            assert side_survival(side).score == pytest.approx(survival(char, f).score)
            assert side_control(side).score == pytest.approx(control(char, f).score)
            assert side_battleground(side, 60)["score"] == pytest.approx(battleground(char, f, a)["score"])
        sides = [(f.name, duel_side(char, f)) for f in fillers]
        best = best_battleground(char, fillers, a)
        side_best = best_side_battleground(sides, 60)
        assert (side_best["score"], side_best["spell"]) == (pytest.approx(best["score"]), best["spell"])


def test_other_classes_get_escapes_and_mana_on_their_side():
    # Sprint and Vanish: 300 s cooldowns each -> 0.2 + 0.2 per minute
    cls, builds = loaded("rogue")
    (_, rogue), = engine("rogue").sides(stat_table("rogue").at(60), cls.spells, cls, builds[0])
    assert rogue.escapes == pytest.approx(0.4) and rogue.mana == 0.0 and rogue.mana_per_second == 0.0
    cls, builds = loaded("priest")
    (_, priest), = engine("priest").sides(stat_table("priest").at(60), cls.spells, cls, builds[0])
    assert priest.mana > 0 and priest.escapes > 0
    assert 0.0 <= side_battleground(priest, 60)["score"] <= 1.0
