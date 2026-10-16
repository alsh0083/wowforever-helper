"""1.60.1.70425 talent changes for warlock, druid and hunter (#358, #359), on the pinned dataset."""

import pytest

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.schema import Dataset, latest_dataset_path

DS = Dataset.load(latest_dataset_path())


def loaded(class_name):
    m = class_module(class_name)
    return attach_effects(DS.class_data(class_name), m.TALENT_EFFECTS, m.UNMODELED)


def effects(cls, name):
    return {(e.kind, e.applies_to): e.values for e in cls.talent_named(name).effects}


@pytest.mark.parametrize("class_name", ["warlock", "druid", "hunter"])
def test_every_talent_maps(class_name):
    assert loaded(class_name)[1] == []


def test_shadow_mastery_is_two_percent_a_rank():
    cls, _ = loaded("warlock")
    assert effects(cls, "Shadow Mastery") == {("damage_pct", ("shadow",)): (2.0, 4.0, 6.0, 8.0, 10.0)}


def test_grim_reach_is_range_only():
    from wowforever.classes.warlock import TALENT_EFFECTS, UNMODELED

    cls, _ = loaded("warlock")
    assert cls.talent_named("Grim Reach").effects == ()
    assert "Grim Reach" in UNMODELED and "Malediction" not in TALENT_EFFECTS


def test_leader_of_the_pack_reads_the_new_text():
    cls, _ = loaded("druid")
    assert effects(cls, "Leader of the Pack") == {("crit_chance", ("@feral",)): (3.0,)}


def test_predators_edge_crits_are_for_melee_abilities():
    cls, _ = loaded("hunter")
    assert effects(cls, "Predator's Edge") == {
        ("crit_damage_pct", ("@ability",)): (6.0, 12.0, 18.0, 24.0, 30.0),
        ("damage_pct", ("@off_hand",)): (10.0, 20.0, 30.0, 40.0, 50.0)}
