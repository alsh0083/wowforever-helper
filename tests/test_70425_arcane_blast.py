"""1.60.1.70425 Arcane Blast (#355, part B): stacks of spell damage from Intellect, bought with a rising mana cost.
Numbers re-pinned on 1.60.1.70755 (#463): 12% of Intellect and +100% mana per stack, 18 s (2 Nov notes)."""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.classes.mage import TALENT_EFFECTS, UNMODELED, _blast_options
from wowforever.classes.mage_rotation import arcane_blast_stacks, rotation
from wowforever.effects import attach_effects
from wowforever.scenarios import Character, best_rank
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.stats import StatTable

from _trees import tree_build

CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("mage"), TALENT_EFFECTS, UNMODELED)
STATS = StatTable.load("mage").at(60)
BUILDS = {tree: tree_build(CLS, tree, "PvE").final_ids(CLS) for tree in ("Arcane", "Frost")}
A = Assumptions.load()


def char(build_id):
    return Character(60, STATS, CLS.spells, CLS, BUILDS[build_id])


def test_the_stack_buff_comes_from_the_rank_text():
    # 70755: 12% of Intellect as Spell Damage and +100% mana cost per stack, up to 4 stacks, 18 sec (2 Nov notes)
    assert arcane_blast_stacks(CLS) == (12.0, 100.0, 4, 18.0)


def test_stack_options_need_the_talent():
    assert list(_blast_options(char("Arcane"))) == [0, 1, 2, 3, 4]
    assert list(_blast_options(char("Frost"))) == [0]


def test_no_stacks_is_the_plain_rotation():
    c = char("Arcane")
    filler = best_rank(c.spells, "Arcane Missiles", 60)
    plain = rotation(c, filler, target_level=63, assumptions=A, sustained=True)
    assert rotation(c, filler, target_level=63, assumptions=A, sustained=True, blast_stacks=0) == plain
    assert "Arcane Blast" not in plain.weaves


def test_one_stack_is_one_arcane_blast_per_window():
    c = char("Arcane")
    filler = best_rank(c.spells, "Frostbolt", 60)
    r = rotation(c, filler, target_level=63, assumptions=A, sustained=True, blast_stacks=1)
    assert r.weaves["Arcane Blast"] == pytest.approx(60 / 18)            # one 18 s window after another


def test_more_stacks_cost_more_mana_and_do_more_damage():
    c = char("Arcane")
    filler = best_rank(c.spells, "Frostbolt", 60)
    runs = [rotation(c, filler, target_level=63, assumptions=A, sustained=True, blast_stacks=n) for n in range(5)]
    assert all(a.dps < b.dps for a, b in zip(runs, runs[1:]))
    assert all(a.mana_per_second < b.mana_per_second for a, b in zip(runs[1:], runs[2:]))
