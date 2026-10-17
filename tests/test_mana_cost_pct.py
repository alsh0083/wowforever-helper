"""Percentage mana costs (#361): wago's SpellPower.PowerCostPct, as a share of the class's base mana at max level."""

import json

import pytest

from wowforever.schema import Dataset, SpellRank, latest_dataset_path

DS = Dataset.load(latest_dataset_path())


def top(class_name, name):
    return [s for s in DS.class_data(class_name).spells if s.name == name][-1]


@pytest.mark.parametrize("class_name, name, pct, cost", [
    ("mage", "Arcane Blast", 15.0, 172),       # 15% of 1150 (config/stats/mage_base.csv, level 60) = 172.5
    ("hunter", "Multi-Shot", 13.9, 111),       # 13.9% of 800
    ("paladin", "Judgement", 6.0, 61),         # 6% of 1020
    ("shaman", "Stormstrike", 8.0, 90),        # 8% of 1130
])
def test_percentage_costs_resolve_at_max_level(class_name, name, pct, cost):
    spell = top(class_name, name)
    assert spell.mana_cost_pct == pytest.approx(pct, abs=1e-6)
    assert spell.mana_cost == cost


def test_flat_costs_are_unchanged():
    frostbolt = top("mage", "Frostbolt")
    assert frostbolt.mana_cost == 290 and frostbolt.mana_cost_pct == 0.0


def test_the_saved_dataset_keeps_the_percentage_not_the_resolved_cost():
    raw = json.loads(latest_dataset_path().read_text(encoding="utf-8"))
    mage = next(c for c in raw["classes"] if c["class_name"] == "mage")
    blast = [s for s in mage["spells"] if s["name"] == "Arcane Blast"][-1]
    assert blast["mana_cost"] == 0 and blast["mana_cost_pct"] == pytest.approx(15.0)


def test_older_datasets_without_the_field_still_load():
    assert SpellRank.__dataclass_fields__["mana_cost_pct"].default == 0.0
