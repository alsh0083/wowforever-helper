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


@pytest.mark.parametrize("name", ["mage"])
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


SCORED = ("rogue", "hunter", "warrior", "druid", "paladin", "priest", "shaman", "warlock")


def test_every_scored_class_but_mage_has_an_engine():
    assert {n for n in SCORED if getattr(class_module(n), "ENGINE", None) in ("melee", "spell")} == set(SCORED)
    for name in SCORED:
        assert all(callable(getattr(engine(name), member)) for member in ENGINE_MEMBERS)


@pytest.mark.parametrize("name", ["priest", "warlock"])
def test_casters_run_the_caster_rotation(name):
    from wowforever.caster import caster_rotation

    cls, builds = loaded(name)
    stats = ms.stat_table(name).at(60)
    for ranks in builds:
        r = caster_rotation(name, stats, cls.spells, cls, ranks, BOSS, drink_mana_per_second=40.0)
        out = engine(name).output(stats, cls.spells, cls, ranks, BOSS, drink_mana_per_second=40.0)
        gross = r.mana_per_second + r.regen_per_second
        assert out.dps == r.dps and out.mana_per_second == r.mana_per_second and out.ranged
        assert out.fallback_dps == pytest.approx(r.dps * min(1.0, r.regen_per_second / gross) if gross else r.dps)
        assert engine(name).playstyle(cls, ranks) == "caster"


@pytest.mark.parametrize("name,melee_build,caster_build", [("druid", "druid-feral", "druid-balance"),
                                                           ("shaman", "shaman-enhancement", "shaman-elemental")])
def test_hybrids_fight_with_the_row_their_main_tree_picks(name, melee_build, caster_build):
    m = class_module(name)
    cls, _ = attach_effects(DATASET.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)
    builds = {b.id: b.final_ids(cls) for b in load_builds(class_name=name)}
    stats = ms.stat_table(name).at(60)
    melee, caster = builds[melee_build], builds[caster_build]
    assert engine(name).playstyle(cls, melee) == "melee" and engine(name).playstyle(cls, caster) == "caster"
    as_melee = engine(name).output(stats, cls.spells, cls, melee, BOSS)
    assert as_melee.mana_per_second == 0.0 and not as_melee.ranged
    as_caster = engine(name).output(stats, cls.spells, cls, caster, BOSS)
    assert as_caster.ranged
    # the melee override wins over the main tree (a Feral leveling path while its points sit in Balance)
    forced = engine(name).output(stats, cls.spells, cls, caster, BOSS, melee=True)
    assert forced.mana_per_second == 0.0 and not forced.ranged


def test_rotation_output_has_no_class_chain():
    import inspect

    src = inspect.getsource(ms.rotation_output) + inspect.getsource(ms.aoe)
    assert "class_name ==" not in src and "HybridStats" not in src and "ENGINE" not in src


KINDS = {"rogue": {"rogue"}, "hunter": {"hunter"}, "warrior": {"abilities"}, "paladin": {"abilities"},
         "priest": {"caster"}, "warlock": {"caster"}, "druid": {"cat", "caster"}, "shaman": {"enhancement", "caster"}}


@pytest.mark.parametrize("name", SCORED)
def test_facts_describe_the_rotation_each_build_runs(name):
    cls, builds = loaded(name)
    stats = ms.stat_table(name).at(60)
    kinds = set()
    for ranks in builds:
        try:
            f = engine(name).facts(stats, cls, ranks)
        except ZeroDivisionError:          # a build whose rotation does no damage at 60 (describe skips it)
            continue
        kinds.add(f["kind"])
        if f["kind"] == "caster":
            assert set(f) == {"kind", "dots", "cooldowns", "filler"}
        else:
            assert sum(f["split"].values()) <= 1.0 + 1e-9
    assert kinds == KINDS[name]


def test_describe_asks_the_engine_for_every_class_but_mage():
    import inspect

    from wowforever import describe

    src = inspect.getsource(describe.rotation_facts)
    assert "_rotation" not in src.replace("rotation_facts", "") and "HybridStats" not in src
