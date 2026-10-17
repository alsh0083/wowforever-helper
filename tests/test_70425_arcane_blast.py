"""1.60.1.70425 Arcane Blast (#355, part B): stacks of spell damage from Intellect, bought with a rising mana cost."""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.classes.mage import TALENT_EFFECTS, UNMODELED, _blast_options
from wowforever.classes.mage_rotation import arcane_blast_stacks, rotation
from wowforever.effects import attach_effects
from wowforever.scenarios import Character, best_rank
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.stats import StatTable

CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("mage"), TALENT_EFFECTS, UNMODELED)
STATS = StatTable.load("mage").at(60)
BUILDS = {b.id: b.final_ids(CLS) for b in load_builds(class_name="mage")}
A = Assumptions.load()


def char(build_id):
    return Character(60, STATS, CLS.spells, CLS, BUILDS[build_id])


def test_the_stack_buff_comes_from_the_rank_text():
    # "you gain 15% of your Intellect as Spell Damage and the mana cost of Arcane Blast is increased by 175%.
    #  Effect stacks up to 4 times and lasts 15 sec from time of initial application."
    assert arcane_blast_stacks(CLS) == (15.0, 175.0, 4, 15.0)


def test_stack_options_need_the_talent():
    assert list(_blast_options(char("deep-arcane"))) == [0, 1, 2, 3, 4]
    assert list(_blast_options(char("deep-frost"))) == [0]


def test_no_stacks_is_the_plain_rotation():
    c = char("deep-arcane")
    filler = best_rank(c.spells, "Arcane Missiles", 60)
    plain = rotation(c, filler, target_level=63, assumptions=A, sustained=True)
    assert rotation(c, filler, target_level=63, assumptions=A, sustained=True, blast_stacks=0) == plain
    assert "Arcane Blast" not in plain.weaves


def test_one_stack_is_one_arcane_blast_per_window():
    c = char("deep-arcane")
    filler = best_rank(c.spells, "Frostbolt", 60)
    r = rotation(c, filler, target_level=63, assumptions=A, sustained=True, blast_stacks=1)
    assert r.weaves["Arcane Blast"] == pytest.approx(60 / 15)            # four 15 s windows a minute


def test_more_stacks_cost_more_mana_and_do_more_damage():
    c = char("deep-arcane")
    filler = best_rank(c.spells, "Frostbolt", 60)
    runs = [rotation(c, filler, target_level=63, assumptions=A, sustained=True, blast_stacks=n) for n in range(5)]
    assert all(a.dps < b.dps for a, b in zip(runs, runs[1:]))
    assert all(a.mana_per_second < b.mana_per_second for a, b in zip(runs[1:], runs[2:]))
