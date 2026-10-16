"""Golden tests for the shared raid with the mage's mechanics (#317, part A).

`melee_scenarios.raid_dps(out, mana, p)`: full DPS while the mana budget lasts, then `fallback_dps`.
Budget = mana + p.extra_mana + each consumable once per started cooldown. When the budget would run
out before the fight ends, a class's `Output.mana_cooldown` (channel seconds, mana: the mage's
Evocation) adds its mana and removes its channel time from the active time.

Hand-worked, one 100 s fight, raid income 8 mana/s, out = 300 DPS, 18 mana/s (drain 10/s), fallback 100:
- 500 mana, no cooldown: dry at 50 s -> (300 x 50 + 100 x 50) / 100 = 200
- with mana_cooldown (8 s, 2000 mana): budget 2500 -> 250 s > 92 s active -> 300 x 92 / 100 = 276
- 500 mana + a (300 mana, 60 s) consumable used twice: 1100 -> dry at 110 s >= 100 -> 300
- drain <= 0 (mana_per_second 8): 300 whatever the mana
- two lengths, 50 s weight 1 and 100 s weight 1, 500 mana, no cooldown: 50 s -> 300, 100 s -> 200 -> 250
"""

from pathlib import Path

import pytest

from wowforever import melee_scenarios as ms
from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.classes import class_module, engine
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import Output, raid_dps
from wowforever.physical import Target
from wowforever.scenarios import Character, RaidParams, default_params, raid
from wowforever.schema import Dataset
from wowforever.stats import StatTable

DATASET = Dataset.load(Path(__file__).resolve().parents[1] / "data" / "datasets" / "1.60.1.70291.json")


def params(lengths=((100.0, 1.0),), consumables=()):
    return RaidParams(fight_seconds=100, mana_per_second=8, fillers=(), fight_lengths=lengths,
                      consumables=consumables)


def out(mana_per_second=18.0, cooldown=None):
    return Output(300.0, mana_per_second, 100.0, mana_cooldown=cooldown)


def test_runs_dry_then_falls_back():
    assert raid_dps(out(), 500, params()) == pytest.approx(200.0)


def test_mana_cooldown_refills_and_costs_its_channel():
    assert raid_dps(out(cooldown=(8.0, 2000.0)), 500, params()) == pytest.approx(276.0)


def test_mana_cooldown_unused_when_the_budget_lasts():
    assert raid_dps(out(cooldown=(8.0, 2000.0)), 5000, params()) == pytest.approx(300.0)


def test_consumables_once_per_started_cooldown():
    assert raid_dps(out(), 500, params(consumables=((300.0, 60.0),))) == pytest.approx(300.0)


def test_no_drain_keeps_full_dps():
    assert raid_dps(out(mana_per_second=8.0), 0, params()) == pytest.approx(300.0)


def test_fight_lengths_are_weighted():
    assert raid_dps(out(), 500, params(lengths=((50.0, 1.0), (100.0, 1.0)))) == pytest.approx(250.0)


def loaded(name):
    m = class_module(name)
    cls, _ = attach_effects(DATASET.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)
    return cls


def test_mage_raid_through_the_shared_path_is_the_mage_model():
    cls, stats, a = loaded("mage"), StatTable.load("mage").at(60), Assumptions.load()
    builds = [b for b in load_builds(class_name="mage") if b.mode != "leveling"]
    assert len(builds) >= 10
    for b in builds:
        ranks = b.final_ids(cls)
        expected = raid(Character(60, stats, cls.spells, cls, dict(ranks)), default_params("raid", 60), a).score
        assert ms.raid("mage", stats, cls.spells, cls, ranks) == pytest.approx(expected, rel=1e-9), b.id


@pytest.mark.parametrize("name", ["rogue", "hunter", "warrior", "paladin", "priest", "warlock", "druid", "shaman"])
def test_other_classes_ignore_sustained(name):
    cls, stats = loaded(name), ms.stat_table(name).at(60)
    ranks = next(b for b in load_builds(class_name=name) if b.mode != "leveling").final_ids(cls)
    target = Target(3, 976)
    assert (engine(name).output(stats, cls.spells, cls, ranks, target, sustained=True)
            == engine(name).output(stats, cls.spells, cls, ranks, target))
