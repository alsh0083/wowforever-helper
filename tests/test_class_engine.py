"""Class engine (#309, #310): each scored class module runs its own rotation behind one interface
(docs/planning/2026-10-14-class-engine.md). A refactor: adapters must equal the rotations they wrap."""

import pytest

from wowforever import melee_scenarios as ms
from wowforever.builds import load_builds
from wowforever.classes import ENGINE_MEMBERS, class_module, engine
from wowforever.classes.hunter import has_pet
from wowforever.classes.hunter_rotation import hunter_rotation
from wowforever.classes.paladin_rotation import paladin_rotation
from wowforever.classes.rogue_rotation import rogue_rotation
from wowforever.classes.warrior_rotation import warrior_rotation
from wowforever.effects import attach_effects
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path

DATASET = Dataset.load(latest_dataset_path())
BOSS = Target(3, 976)
ADAPTED = {"rogue": rogue_rotation, "warrior": warrior_rotation, "paladin": paladin_rotation}


def loaded(name):
    m = class_module(name)
    cls, _ = attach_effects(DATASET.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)
    return cls, [b.final_ids(cls) for b in load_builds(class_name=name)]


@pytest.mark.parametrize("name", sorted(ADAPTED))
def test_adapted_classes_implement_the_class_engine(name):
    module = engine(name)
    assert all(callable(getattr(module, member)) for member in ENGINE_MEMBERS)


@pytest.mark.parametrize("name", ["mage", "druid"])
def test_classes_without_an_adapter_yet_have_no_engine(name):
    with pytest.raises(ValueError, match=name):
        engine(name)


def test_output_has_no_pet_and_fights_in_melee_by_default():
    out = ms.Output(10.0, 0.0, 10.0)
    assert (out.aoe, out.pet, out.ranged) == ((), False, False)


@pytest.mark.parametrize("name", sorted(ADAPTED))
@pytest.mark.parametrize("pack", [1, 3])
def test_output_wraps_the_class_rotation(name, pack):
    cls, builds = loaded(name)
    stats = ms.stat_table(name).at(60)
    for ranks in builds:
        r = ADAPTED[name](stats, cls.spells, cls, ranks, BOSS, pack=pack)
        out = engine(name).output(stats, cls.spells, cls, ranks, BOSS, pack=pack)
        assert out == ms.Output(r.dps, 0.0, r.dps, r.aoe)
        assert engine(name).playstyle(cls, ranks) == "melee"
        assert ms.rotation_output(name, stats, cls.spells, cls, ranks, BOSS, pack=pack) == out


@pytest.mark.parametrize("name", sorted(ADAPTED))
def test_aoe_clears_the_pack_with_the_pack_rotation(name):
    cls, builds = loaded(name)
    stats = ms.stat_table(name).at(60)
    for ranks in builds:
        out = engine(name).output(stats, cls.spells, cls, ranks, Target(0, 500.0), pack=3)
        seconds, used = engine(name).aoe(stats, cls.spells, cls, ranks, pack=3, mob_hp=1200.0, armor=500.0)
        assert seconds == pytest.approx(3 * 1200.0 / out.dps)
        assert used == (", ".join(out.aoe) or "single target")


def test_hunter_output_carries_its_pet_and_range():
    cls, builds = loaded("hunter")
    stats = ms.stat_table("hunter").at(60)
    assert {has_pet(cls, ranks) for ranks in builds} == {True, False}      # Lone Wolf builds fight alone
    for ranks in builds:
        for pack in (1, 3):
            pet = has_pet(cls, ranks)
            r = hunter_rotation(stats, cls.spells, cls, ranks, BOSS, pet=pet, pack=pack)
            out = engine("hunter").output(stats, cls.spells, cls, ranks, BOSS, pack=pack)
            assert out == ms.Output(r.dps, r.mana_per_second, r.auto_dps + r.pet_dps, r.aoe,
                                    pet=pet, ranged=r.mode == "ranged")
            assert ms.rotation_output("hunter", stats, cls.spells, cls, ranks, BOSS, pack=pack) == out
        assert engine("hunter").playstyle(cls, ranks) == "ranged"
        seconds, _ = engine("hunter").aoe(stats, cls.spells, cls, ranks, pack=3, mob_hp=1200.0, armor=500.0)
        assert seconds == pytest.approx(3 * 1200.0 / engine("hunter").output(
            stats, cls.spells, cls, ranks, Target(0, 500.0), pack=3).dps)


def test_only_the_hunter_module_knows_about_pets():
    import wowforever.melee_scenarios as module

    assert not hasattr(module, "_has_pet")
