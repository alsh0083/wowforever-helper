"""One outnumbered (2v1) path for every class (#317, part C).

`pvp.duel.best_outnumbered(sides, kits)` gives the 2v1 score of the build's best duel side and that
side's name: the mage's filler, or None for a class with one unnamed side. The mage's and the other
classes' report rows both use it; `class_pvp.outnumbered_score` goes.
"""

import inspect
from pathlib import Path

import pytest

from wowforever import report
from wowforever.builds import load_builds
from wowforever.classes import class_module, engine
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.pvp import class_pvp
from wowforever.pvp.duel import best_outnumbered, load_kits, outnumbered_scores
from wowforever.schema import Dataset

DATASET = Dataset.load(Path(__file__).resolve().parents[1] / "data" / "datasets" / "1.60.1.70291.json")
KITS = load_kits()


def sides_of(name, build):
    m = class_module(name)
    cls, _ = attach_effects(DATASET.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)
    ranks = next(b for b in load_builds(class_name=name) if b.id == build).final_ids(cls)
    return engine(name).sides(stat_table(name).at(60), cls.spells, cls, ranks)


def test_no_sides_is_an_even_fight():
    assert best_outnumbered([], KITS) == (0.5, None)


def test_a_class_with_one_unnamed_side():
    sides = sides_of("rogue", "rogue-subtlety-pvp")
    assert best_outnumbered(sides, KITS) == (outnumbered_scores(sides[0][1], KITS)["score"], None)


def test_the_mage_takes_its_best_filler():
    sides = sides_of("mage", "deep-frost")
    assert len(sides) > 1
    scores = {name: outnumbered_scores(side, KITS)["score"] for name, side in sides}
    score, spell = best_outnumbered(sides, KITS)
    assert score == pytest.approx(max(scores.values()))
    assert scores[spell] == score


def test_one_path():
    assert not hasattr(class_pvp, "outnumbered_score")
    source = inspect.getsource(report)
    assert "outnumbered_scores(" not in source
    assert source.count("best_outnumbered(") == 2
