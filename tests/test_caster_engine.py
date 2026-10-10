"""Caster spell engine (#163) with the Shadow priest as its first class (#164)."""

import json
from pathlib import Path

import pytest

from wowforever.schema import latest_dataset_path
from wowforever.builds import load_builds
from wowforever.caster import caster_rotation, spirit_regen
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import raid, rotation_output, stat_table
from wowforever.physical import Target
from wowforever.pvp.class_pvp import class_side
from wowforever.schema import Dataset
from wowforever.stats import Stats

ROOT = Path(__file__).resolve().parents[1]
DATASET = Dataset.load(latest_dataset_path())
P = class_module("priest")
CLS, PROBLEMS = attach_effects(DATASET.class_data("priest"), P.TALENT_EFFECTS, P.UNMODELED)
BUILDS = {b.id: b.final_ids(CLS) for b in load_builds(class_name="priest")}
STATS = stat_table("priest").at(60)
BOSS = Target(3, 0)


def without(ranks, name):
    tid = CLS.talent_named(name).talent_id
    return {t: r for t, r in ranks.items() if t != tid}


def test_casters_get_a_mage_format_stat_table():
    assert isinstance(STATS, Stats) and STATS.spell_power > 200 and STATS.mana > 3000


def test_rules_use_lowercase_schools_and_parse():
    assert PROBLEMS == []
    weaving = CLS.talent_named("Shadow Weaving").effects[0]
    assert weaving.applies_to == ("shadow",) and weaving.values[-1] == 10      # 100% x 2% x 5 stacks


def test_shadow_rotation_keeps_dots_up_and_flays():
    r = caster_rotation("priest", STATS, CLS.spells, CLS, BUILDS["priest-shadow"], BOSS)
    assert r.spells[0] == "Shadow Word: Pain" and r.spells[-1] == "Mind Flay" and "Mind Blast" in r.spells
    assert r.dps > caster_rotation("priest", STATS, CLS.spells, CLS, BUILDS["priest-holy"], BOSS).dps


@pytest.mark.parametrize("talent", ["Shadowform", "Darkness", "Shadow Weaving", "Improved Mind Blast"])
def test_each_shadow_talent_raises_dps(talent):
    full = caster_rotation("priest", STATS, CLS.spells, CLS, BUILDS["priest-shadow"], BOSS).dps
    assert caster_rotation("priest", STATS, CLS.spells, CLS, without(BUILDS["priest-shadow"], talent), BOSS).dps < full


def test_meditation_pays_part_of_the_mana():
    r = caster_rotation("priest", STATS, CLS.spells, CLS, BUILDS["priest-shadow"], BOSS)
    assert r.regen_per_second == pytest.approx(spirit_regen("priest", STATS) * 0.5)


def test_raid_is_mana_limited_but_shadowform_halves_costs():
    out = rotation_output("priest", STATS, CLS.spells, CLS, BUILDS["priest-shadow"], BOSS)
    assert 0 < out.fallback_dps < out.dps
    assert raid("priest", STATS, CLS.spells, CLS, BUILDS["priest-shadow"]) > raid(
        "priest", STATS, CLS.spells, CLS, without(BUILDS["priest-shadow"], "Shadowform"))


def test_pvp_side_and_report():
    side = class_side("priest", STATS, CLS.spells, CLS, BUILDS["priest-shadow"])
    # the community Shadow build skips Silence, so only Psychic Scream and Blackout lock the opponent
    assert side.stun > 0 and side.interrupt == 0 and side.physical_taken == pytest.approx(1.0)
    r = json.loads((ROOT / "data" / "report-priest.json").read_text(encoding="utf-8"))
    slots = {(s["archetype"], s["focus"]): s for s in r["shortlist"]}
    assert r["engine"] is True and r["caveats"][0].startswith("Caster model (#163)")
    assert 0 < slots[("deep Shadow", "PvP")]["standard_score"] < 1
    assert slots[("deep Discipline", "PvP")]["standard_score"] is not None          # Smite is damage
    assert slots[("deep Discipline", "PvE")]["standard_score"] is None              # healer build
    assert all(s["standard_score"] is None for (a, _), s in slots.items() if a == "deep Holy")
