"""Retribution paladin on the melee engine (#175)."""

import json
from pathlib import Path

import pytest

from wowforever.schema import latest_dataset_path
from wowforever.classes import class_module
from wowforever.classes.paladin_rotation import paladin_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.pvp.class_pvp import class_side
from wowforever.schema import Dataset

from _trees import builds_by_id

ROOT = Path(__file__).resolve().parents[1]
M = class_module("paladin")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("paladin"),
                               M.TALENT_EFFECTS, M.UNMODELED)
RET = {k: b.final_ids(CLS) for k, b in builds_by_id("paladin").items()}["paladin-retribution"]
STATS = stat_table("paladin").at(60)
BOSS = Target(3, 976)


def without(ranks, name):
    tid = CLS.talent_named(name).talent_id
    return {t: r for t, r in ranks.items() if t != tid}


def test_rules_parse():
    assert PROBLEMS == [] and M.ENGINE == "melee"
    assert CLS.talent_named("Vengeance").effects[0].values[-1] == 15         # 3% x 5 stacks since 70755 (3 before)


def test_retribution_uses_seal_judgement_and_holy_strike():
    r = paladin_rotation(STATS, CLS.spells, CLS, RET, BOSS)
    assert r.abilities == ("Seal of Command", "Judgement", "Holy Strike", "Hammer of Wrath", "Consecration")   # #399
    assert r.holy_dps > 0.3 * r.dps


def test_holy_damage_ignores_armor():
    light = paladin_rotation(STATS, CLS.spells, CLS, RET, Target(3, 0))
    heavy = paladin_rotation(STATS, CLS.spells, CLS, RET, Target(3, 5000))
    assert heavy.holy_dps == pytest.approx(light.holy_dps) and heavy.white_dps < light.white_dps


@pytest.mark.parametrize("talent", ["Seal of Command", "Conviction", "Two-Handed Weapon Specialization",
                                    "Vengeance", "Sacred Arbiter", "Improved Judgement"])
def test_each_talent_raises_dps(talent):
    full = paladin_rotation(STATS, CLS.spells, CLS, RET, BOSS).dps
    assert paladin_rotation(STATS, CLS.spells, CLS, without(RET, talent), BOSS).dps < full


def test_pvp_side_and_report():
    side = class_side("paladin", STATS, CLS.spells, CLS, RET)
    assert side.stun > 0 and side.physical_taken < 1
    r = json.loads((ROOT / "data" / "report-paladin.json").read_text(encoding="utf-8"))
    slots = {(s["archetype"], s["focus"]): s for s in r["shortlist"]}
    assert r["engine"] is True and r["caveats"][0].startswith("Retribution model (#175)")
    assert slots[("deep Retribution", "PvP")]["standard_score"] > 0
    assert all(s["standard_score"] is None for (a, _), s in slots.items() if a in ("deep Holy", "deep Protection"))
