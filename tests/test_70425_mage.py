"""1.60.1.70425 mage talents (#354), on the pinned dataset."""

import pytest

from wowforever.classes.mage import TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.schema import Dataset, latest_dataset_path

CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("mage"), TALENT_EFFECTS, UNMODELED)


def effects(name):
    return {(e.kind, e.applies_to): e.values for e in CLS.talent_named(name).effects}


def test_every_mage_talent_maps():
    assert PROBLEMS == []
    assert "Wake of Fire" not in TALENT_EFFECTS and "Winter's Chill" in UNMODELED


def test_critical_mass_is_two_percent_a_rank():
    assert effects("Critical Mass") == {("crit_chance", ("fire",)): (2.0, 4.0, 6.0, 8.0, 10.0)}


def test_fire_power_counts_the_assumed_fire_effects_up_to_its_cap():
    from wowforever.assumptions import Assumptions

    n = Assumptions.load()["fire_power_effects"]
    assert n == 2                                   # Ignite and Fireball's DoT (config/assumptions.toml)
    assert effects("Fire Power") == {("damage_pct", ("fire",)): (2.0, 4.0, 6.0)}


def test_improved_frostbolt_also_speeds_frost_blast():
    assert effects("Improved Frostbolt") == {("cast_time", ("Frostbolt", "Frost Blast")): (-0.1, -0.2, -0.3, -0.4, -0.5)}


def test_improved_fire_blast_cuts_the_cooldown():
    assert effects("Improved Fire Blast") == {("cooldown", ("Fire Blast",)): (-1.0, -2.0)}


def test_winters_chill_no_longer_adds_crit():
    assert CLS.talent_named("Winter's Chill").effects == ()


def test_ice_lance_frozen_multiplier_reads_the_rank_text():
    from wowforever.classes.mage_rotation import frozen_lance_multiplier

    assert frozen_lance_multiplier(CLS) == pytest.approx(3.0)      # +200% on 1.60.1.70425 (was +300%)
