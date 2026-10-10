"""Warlock, Balance druid and Elemental shaman on the caster engine (#165, #166, #167)."""

import json
from pathlib import Path

import pytest

from wowforever.schema import latest_dataset_path
from wowforever.builds import load_builds
from wowforever.caster import caster_rotation
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.pvp.class_pvp import class_side
from wowforever.schema import Dataset

ROOT = Path(__file__).resolve().parents[1]
DATASET = Dataset.load(latest_dataset_path())
BOSS = Target(3, 0)


def loaded(name):
    m = class_module(name)
    cls, problems = attach_effects(DATASET.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)
    return cls, problems, {b.id: b.final_ids(cls) for b in load_builds(class_name=name)}


def rotation(name, build):
    cls, _, builds = loaded(name)
    stats = stat_table(name).at(60)
    return caster_rotation(name, getattr(stats, "caster", stats), cls.spells, cls, builds[build], BOSS)


@pytest.mark.parametrize("name", ["warlock", "druid", "shaman"])
def test_rules_parse_and_engine_is_spell(name):
    assert loaded(name)[1] == [] and class_module(name).ENGINE == "spell"


def test_spells_taught_by_talents_need_the_talent():
    assert "Conflagrate" not in rotation("warlock", "warlock-affliction").spells
    assert "Conflagrate" in rotation("warlock", "warlock-destruction").spells
    assert "Insect Swarm" in rotation("druid", "druid-balance").spells
    assert "Lava Burst" in rotation("shaman", "shaman-elemental").spells


def test_life_tap_pays_part_of_the_warlocks_mana():
    assert rotation("warlock", "warlock-affliction").regen_per_second >= 15


def test_balance_beats_an_untalented_caster_rotation():
    assert rotation("druid", "druid-balance").dps > 1.3 * rotation("druid", "druid-restoration").dps


def test_roots_count_in_pvp():
    cls, _, builds = loaded("druid")
    side = class_side("druid", stat_table("druid").at(60), cls.spells, cls, builds["druid-balance"])
    assert side.root > 0


@pytest.mark.parametrize("name,scored,unscored", [
    ("warlock", {"deep Affliction", "deep Demonology", "deep Destruction"}, set()),
    ("druid", {"deep Balance", "deep Feral Combat"}, {"deep Restoration"}),
    ("shaman", {"deep Elemental", "deep Enhancement"}, {"deep Restoration"}),
])
def test_reports_score_damage_specs_only(name, scored, unscored):
    r = json.loads((ROOT / "data" / f"report-{name}.json").read_text(encoding="utf-8"))
    for s in r["shortlist"]:
        if s["standard"] and s["archetype"] in scored and s["standard"] != "druid-feral-bear":
            assert s["standard_score"] is not None
        if s["archetype"] in unscored:
            assert s["standard_score"] is None and s["model_pick"] is None
