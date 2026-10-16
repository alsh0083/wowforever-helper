"""1.60.1.70425 mage fillers (#355, part A): Frost Blast, and Arcane Wrath with its spell damage from maximum mana."""

import pytest

from wowforever.classes.mage import TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.scenarios import Character, best_rank, default_params
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.stats import StatTable

CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("mage"), TALENT_EFFECTS, UNMODELED)
STATS = StatTable.load("mage").at(60)
WRATH = CLS.talent_named("Arcane Wrath").talent_id
PYRO = CLS.talent_named("Pyroblast").talent_id


def char(ranks):
    return Character(60, STATS, CLS.spells, CLS, ranks)


def test_new_fillers_are_in_the_config():
    assert default_params("questing", 60).fillers[-2:] == ("Frost Blast", "Arcane Wrath")


def test_a_talent_taught_spell_needs_its_talent():
    bare = char({})
    assert best_rank(bare.spells, "Arcane Wrath", 60) is None
    assert best_rank(bare.spells, "Pyroblast", 60) is None
    assert best_rank(bare.spells, "Frostbolt", 60) is not None          # baseline spells stay
    assert best_rank(char({PYRO: 1}).spells, "Pyroblast", 60) is not None


def test_arcane_wrath_gains_five_percent_of_max_mana_as_spell_damage():
    raw = best_rank(CLS.spells, "Arcane Wrath", 60)
    learned = best_rank(char({WRATH: 1}).spells, "Arcane Wrath", 60)
    extra = raw.coefficient * 0.05 * STATS.mana             # coefficient 1.0 x 5% of max mana
    assert learned.min_damage == pytest.approx(raw.min_damage + extra)
    assert learned.max_damage == pytest.approx(raw.max_damage + extra)
    assert best_rank(char({WRATH: 1}).spells, "Frostbolt", 60) == best_rank(CLS.spells, "Frostbolt", 60)


def test_frost_blast_is_a_baseline_filler():
    spell = best_rank(char({}).spells, "Frost Blast", 60)
    assert spell is not None and spell.cast_time == 1.5 and spell.slow_pct == 40.0
