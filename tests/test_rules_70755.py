"""Effect rules on build 1.60.1.70755 with the 3 Nov hotfixes (#463-#469): every talent is covered, and the reworked
talents read the hand-checked numbers from their rank text. Reads the saved 70755 dataset, not the pin."""

from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.schema import DATASETS_DIR, Dataset

DS = Dataset.load(DATASETS_DIR / "1.60.1.70755.json")


def effects(cls_name):
    m = class_module(cls_name)
    cls, problems = attach_effects(DS.class_data(cls_name), m.TALENT_EFFECTS, m.UNMODELED)
    return cls, problems


def rules(cls, name):
    return [(e.kind, tuple(e.applies_to), tuple(e.values)) for e in cls.talent_named(name).effects]


def test_rogue():
    cls, problems = effects("rogue")
    assert problems == []
    assert rules(cls, "Coup de Grace") == [("damage_pct", ("Eviscerate",), (7.0, 13.0, 20.0))]
    assert rules(cls, "Efficient Strikes") == [("energy_cost", ("Sinister Strike", "Hemorrhage"), (-3.0, -5.0))]
    assert rules(cls, "Aggression") == [("damage_pct", ("Sinister Strike", "Eviscerate"), (5.0, 10.0, 15.0))]
    assert rules(cls, "Lethality")[0][2] == (10.0, 20.0)
    assert rules(cls, "Seal Fate") == [("proc_chance", ("@builder_crit",), (33.0, 66.0, 100.0))]
    assert rules(cls, "Dual Wield Specialization") == [("damage_pct", ("@off_hand",), (25.0, 50.0))]


def test_mage():
    cls, problems = effects("mage")
    assert problems == []
    assert rules(cls, "Accelerant") == [
        ("cast_time", ("Fireball", "Frostfire Bolt", "Arcane Wrath"), (-0.1, -0.2, -0.3, -0.4, -0.5))]
    assert rules(cls, "Precision") == [("hit_chance", ("all",), (2.0, 4.0, 6.0))]


def test_warrior():
    cls, problems = effects("warrior")
    assert problems == []
    assert rules(cls, "Improved Whirlwind") == [("cooldown", ("Whirlwind",), (-1.0, -2.0))]
    assert rules(cls, "Improved Slam") == [("cooldown", ("Slam",), (-2.5, -5.0))]


def test_druid():
    cls, problems = effects("druid")
    assert problems == []
    assert rules(cls, "Naturalist") == [
        ("cast_time", ("Healing Touch", "Wild Growth"), (-0.1, -0.2, -0.3, -0.4, -0.5)),
        ("damage_pct", ("all",), (2.0, 4.0, 6.0, 8.0, 10.0))]


def test_paladin():
    cls, problems = effects("paladin")
    assert problems == []
    assert rules(cls, "Conviction") == [("crit_chance", ("all",), (2.0, 4.0, 6.0))]
    assert rules(cls, "Two-Handed Weapon Specialization") == [("damage_pct", ("@two_hand",), (2.0, 4.0, 6.0))]
    assert rules(cls, "Holy Power") == [
        ("crit_damage_pct", ("Holy Light", "Flash of Light", "Holy Shock"), (10.0, 20.0, 30.0, 40.0, 50.0))]


def test_priest():
    _, problems = effects("priest")
    assert problems == []


def test_warlock():
    cls, problems = effects("warlock")
    assert problems == []
    assert rules(cls, "Improved Drains") == [("damage_pct", ("Drain Life", "Drain Soul"), (7.0, 13.0, 20.0))]


def test_hunter():
    _, problems = effects("hunter")
    assert problems == []


@pytest.mark.parametrize("buff", ["leader_of_the_pack", "moonkin_aura"])
def test_druid_crit_auras_give_all_crit_and_share_one_group(buff):
    import tomllib

    config = tomllib.loads((Path(__file__).resolve().parents[1] / "config" / "group_buffs.toml").read_text("utf-8"))
    entry = next(b for b in config["buff"] if b["id"] == buff)
    assert (entry["aura"], entry["stack"], entry["reach"]) == (290, "druid_form_crit", "party")
