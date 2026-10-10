"""Melee hybrids (#175): Feral cat and Enhancement run on the melee engine inside caster classes."""

import json
from pathlib import Path

import pytest

from wowforever.schema import latest_dataset_path
from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.druid_rotation import cat_rotation
from wowforever.classes.shaman_rotation import enhancement_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import HybridStats, main_tree, rotation_output, stat_table
from wowforever.physical import Target
from wowforever.schema import Dataset

ROOT = Path(__file__).resolve().parents[1]
DATASET = Dataset.load(latest_dataset_path())
BOSS = Target(3, 976)


def loaded(name):
    m = class_module(name)
    cls, problems = attach_effects(DATASET.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)
    return cls, problems, {b.id: b.final_ids(cls) for b in load_builds(class_name=name)}


def without(cls, ranks, name):
    tid = cls.talent_named(name).talent_id
    return {t: r for t, r in ranks.items() if t != tid}


@pytest.mark.parametrize("name,melee,caster", [("druid", "druid-feral", "druid-balance"),
                                                ("shaman", "shaman-enhancement", "shaman-elemental")])
def test_builds_pick_their_engine_by_main_tree(name, melee, caster):
    cls, problems, builds = loaded(name)
    stats = stat_table(name).at(60)
    assert problems == [] and isinstance(stats, HybridStats)
    assert main_tree(cls, builds[melee]) in class_module(name).MELEE_TREES
    assert main_tree(cls, builds[caster]) not in class_module(name).MELEE_TREES
    melee_out = rotation_output(name, stats, cls.spells, cls, builds[melee], BOSS)
    assert melee_out.mana_per_second == 0 and melee_out.dps > 100


@pytest.mark.parametrize("talent", ["Predatory Strikes", "Sharpened Claws", "Savage Fury", "Predatory Instincts"])
def test_cat_talents_raise_dps(talent):
    cls, _, builds = loaded("druid")
    stats = stat_table("druid").at(60).melee
    full = cat_rotation(stats, cls.spells, cls, builds["druid-feral"], BOSS).dps
    assert cat_rotation(stats, cls.spells, cls, without(cls, builds["druid-feral"], talent), BOSS).dps < full


def test_feral_crit_talents_stay_out_of_balance_spells():
    from wowforever.calc.talents import modifiers_for
    from wowforever.scenarios import best_rank

    cls, _, builds = loaded("druid")
    starfire = best_rank(cls.spells, "Starfire", 60)
    assert modifiers_for(starfire, cls, builds["druid-feral"]).crit_chance_bonus < 6       # not +6 Sharpened Claws


@pytest.mark.parametrize("talent", ["Flurry", "Stormstrike", "Elemental Weapons", "Mental Dexterity"])
def test_enhancement_talents_raise_dps(talent):
    cls, _, builds = loaded("shaman")
    stats = stat_table("shaman").at(60).melee
    full = enhancement_rotation(stats, cls.spells, cls, builds["shaman-enhancement"], BOSS).dps
    assert enhancement_rotation(stats, cls.spells, cls, without(cls, builds["shaman-enhancement"], talent), BOSS).dps < full


def test_reports_score_feral_and_enhancement_but_not_the_bear():
    druid = {(s["archetype"], s["focus"]): s for s in
             json.loads((ROOT / "data" / "report-druid.json").read_text(encoding="utf-8"))["shortlist"]}
    assert druid[("deep Feral Combat", "PvP")]["standard_score"] > 0
    assert druid[("deep Feral Combat", "PvE")]["standard_score"] is None                  # bear tank
    shaman = {(s["archetype"], s["focus"]): s for s in
              json.loads((ROOT / "data" / "report-shaman.json").read_text(encoding="utf-8"))["shortlist"]}
    assert shaman[("deep Enhancement", "PvP")]["standard_score"] > 0
    assert shaman[("deep Enhancement", "PvE")]["standard_score"] > 0
