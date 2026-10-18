"""Class engine (#309, #310): each scored class module runs its own rotation behind one interface
(docs/planning/2026-10-14-class-engine.md). A refactor: adapters must equal the rotations they wrap."""

from dataclasses import replace

import pytest

from wowforever import melee_scenarios as ms
from wowforever.builds import load_builds
from wowforever.classes import ENGINE_MEMBERS, class_module, engine
from wowforever.classes.engines import melee_talent_stats
from wowforever.classes.hunter import has_pet
from wowforever.classes.hunter_rotation import hunter_rotation
from wowforever.classes.paladin_rotation import paladin_rotation
from wowforever.classes.rogue_rotation import rogue_rotation
from wowforever.classes.warrior_rotation import warrior_rotation
from wowforever.effects import attach_effects
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.weapon_talents import best_weapon

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


def test_an_unscored_class_has_no_engine(monkeypatch):
    import types

    import wowforever.classes as classes

    monkeypatch.setitem(classes.CLASSES, "nobody", "types")      # a module without the engine functions
    with pytest.raises(ValueError, match="nobody"):
        engine("nobody")


def test_output_has_no_pet_and_fights_in_melee_by_default():
    out = ms.Output(10.0, 0.0, 10.0)
    assert (out.aoe, out.pet, out.ranged) == ((), False, False)


@pytest.mark.parametrize("name", sorted(ADAPTED))
@pytest.mark.parametrize("pack", [1, 3])
def test_output_wraps_the_class_rotation(name, pack):
    cls, builds = loaded(name)
    stats = ms.stat_table(name).at(60)
    for ranks in builds:
        row = melee_talent_stats(name, stats, cls, ranks) if name == "paladin" else stats   # #383
        fury = name == "warrior" and ms.main_tree(cls, ranks) == "Fury"       # only Fury dual wields (#391)
        rows = (row, class_module("warrior").dual_wield(row)) if fury else (row,)
        r = max((best_weapon(lambda s, t: ADAPTED[name](s, cls.spells, cls, ranks, t, pack=pack),
                             w, BOSS, cls, ranks)[0] for w in rows),          # weapon-type talents (#386)
                key=lambda rot: rot.dps)
        if name == "rogue":   # or a dagger and Backstab, whichever scores higher (#392)
            stab = best_weapon(lambda s, t: ADAPTED[name](s, cls.spells, cls, ranks, t, pack=pack, backstab=True),
                               class_module("rogue").dagger(stats), BOSS, cls, ranks, only="dagger")[0]
            r = max(r, stab, key=lambda rot: rot.dps)
        out = engine(name).output(stats, cls.spells, cls, ranks, BOSS, pack=pack)
        if name == "paladin":   # Retribution tracks mana and swings white once dry (#399)
            # plus the rotation without Consecration as an alternative (#399)
            assert replace(out, alternatives=()) == ms.Output(r.dps, r.mana_per_second, r.white_dps, r.aoe)
        else:      # the rogue's questing opener rides along (#431)
            assert out == ms.Output(r.dps, 0.0, r.dps, r.aoe, opener_damage=getattr(r, "opener_damage", 0.0))
        assert engine(name).playstyle(cls, ranks) == "melee"


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
        if name == "warlock":       # once dry, the warlock taps (#348)
            from wowforever.caster import life_tap_pct
            from wowforever.classes.engines import life_tap_fallback
            from wowforever.gear import caster_config

            expected = life_tap_fallback(r.dps, r.mana_per_second, 60, caster_config("warlock")["life_tap"],
                                         bonus_pct=life_tap_pct(cls, ranks))     # Improved Life Tap (#396)
        else:
            expected = r.dps * min(1.0, r.regen_per_second / gross) if gross else r.dps
        assert out.fallback_dps == pytest.approx(expected)
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
    # Enhancement spends mana on shocks and Stormstrike (#398); Feral has none
    assert (as_melee.mana_per_second == 0.0) == (name == "druid") and not as_melee.ranged
    as_caster = engine(name).output(stats, cls.spells, cls, caster, BOSS)
    assert as_caster.ranged
    # the melee override wins over the main tree (a Feral leveling path while its points sit in Balance)
    forced = engine(name).output(stats, cls.spells, cls, caster, BOSS, melee=True)
    assert (forced.mana_per_second == 0.0) == (name == "druid") and not forced.ranged


def test_scenarios_ask_the_engine_with_no_class_chain():
    import inspect

    assert not hasattr(ms, "rotation_output")                 # callers use engine(name).output (#313)
    src = inspect.getsource(ms.aoe) + inspect.getsource(ms.build_stats)
    assert "class_name ==" not in src and "MELEE_TREES" not in src and "ENGINE" not in src


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


def test_mage_implements_the_class_engine_next_to_its_scenarios():
    # #316: the mage's adapter picks its filler like the caster engine; its facts name the spells its
    # own scenarios (scenarios.py) pick, so the build descriptions don't change
    from wowforever.assumptions import Assumptions
    from wowforever.classes.mage_rotation import rotation
    from wowforever.scenarios import Character, best_rank, default_params, questing, usable_fillers
    from wowforever.stats import StatTable

    cls, builds = loaded("mage")
    stats = StatTable.load("mage").at(60)
    mage = engine("mage")
    assert all(callable(getattr(mage, member)) for member in ENGINE_MEMBERS)
    for ranks in builds:
        assert mage.playstyle(cls, ranks) == "caster"
        out = mage.output(stats, cls.spells, cls, ranks, BOSS)
        char = Character(60, stats, cls.spells, cls, dict(ranks))
        a = Assumptions.load()
        best = max((rotation(char, f, target_level=63, assumptions=a, sustained=False).dps, f.name)
                   for f in usable_fillers(char, default_params("questing", 60).fillers, 63, a))
        if out.dps == pytest.approx(best[0]):
            assert out.spell == best[1]
        else:   # an Arcane Blast build may open buff windows with stacks (#355): never below the plain rotation
            assert out.dps > best[0] and best_rank(char.spells, "Arcane Blast", 60) is not None
        assert out.ranged and out.fallback_dps <= out.dps
        facts = mage.facts(stats, cls, ranks)
        assert facts["kind"] == "mage"
        assert facts["questing"] == questing(char, default_params("questing", 60), a).details["spell"]
        seconds, spell = mage.aoe(stats, cls.spells, cls, ranks, pack=3, mob_hp=2000.0, armor=0.0)
        assert seconds > 0 and spell


def test_the_duel_model_knows_no_class():
    # #318: pvp/duel.py scores a Side; the mage builds its sides in its class module like every class
    import inspect

    from wowforever.pvp import duel

    src = inspect.getsource(duel)
    assert "mage_rotation" not in src and "pvp_axes" not in src and "MageSide" not in src
    assert {f.name for f in __import__("dataclasses").fields(duel.Side)} >= {"absorb_per_min", "melee_bonus_dps"}


@pytest.mark.parametrize("name", SCORED + ("mage",))
def test_sides_name_the_filler_only_where_the_class_chooses_one(name):
    from wowforever.pvp.duel import Side
    from wowforever.stats import StatTable

    cls, builds = loaded(name)
    stats = StatTable.load("mage").at(60) if name == "mage" else ms.stat_table(name).at(60)
    sides = engine(name).sides(stats, cls.spells, cls, builds[0])
    assert sides and all(isinstance(side, Side) for _, side in sides)
    if name == "mage":
        assert all(spell for spell, _ in sides) and len(sides) > 1
    else:
        assert [spell for spell, _ in sides] == [None]
