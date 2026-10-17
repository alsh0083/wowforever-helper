"""Attack-speed procs (#391, #393): warrior Flurry (+25% for 3 swings after a crit) and hunter Deadly Aspects
(10% per Auto Shot for +30% ranged speed over 12 s while Aspect of the Hawk is up), as average uptimes."""

import pytest

from wowforever.classes import class_module
from wowforever.classes.hunter_rotation import hunter_rotation
from wowforever.classes.warrior_rotation import warrior_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Attacker, Target, yellow_crit_chance
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

DS = Dataset.load(latest_dataset_path())
BOSS = Target(3, 0)


def loaded(name):
    m = class_module(name)
    return attach_effects(DS.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)


def only(cls, name):
    t = cls.talent_named(name)
    return {t.talent_id: t.max_rank}


@pytest.mark.parametrize("name", ["warrior", "hunter"])
def test_rules_parse(name):
    assert loaded(name)[1] == []


def test_flurry_uptime_hastes_white_swings():
    cls, _ = loaded("warrior")
    stats = stat_table("warrior").at(60)
    base = warrior_rotation(stats, cls.spells, cls, {}, BOSS)
    flurry = warrior_rotation(stats, cls.spells, cls, only(cls, "Flurry"), BOSS)
    crit = yellow_crit_chance(Attacker(60, stats.attack_power, stats.crit_pct, stats.hit_pct), BOSS)
    # 25% faster while any of the last 3 swings critted: 1 + 0.25 x (1 - (1 - crit)^3)
    assert flurry.white_dps == pytest.approx(base.white_dps * (1 + 0.25 * (1 - (1 - crit) ** 3)))


def test_deadly_aspects_uptime_hastes_auto_shot():
    cls, _ = loaded("hunter")
    stats = stat_table("hunter").at(60)
    base = hunter_rotation(stats, cls.spells, cls, {}, BOSS)
    deadly = hunter_rotation(stats, cls.spells, cls, only(cls, "Deadly Aspects"), BOSS)
    rapid = best_rank(cls.spells, "Rapid Fire", 60)
    haste = 1.15 * (1 + rapid.haste_pct / 100 * rapid.duration / rapid.cooldown)
    shots = 12 * haste / stats.ranged[2]                 # Auto Shots in one 12 s window
    assert deadly.auto_dps == pytest.approx(base.auto_dps * (1 + 0.30 * (1 - 0.9 ** shots)))


def test_deadly_aspects_needs_the_hawk():
    cls, _ = loaded("hunter")
    stats = stat_table("hunter").at(60)
    no_hawk = [s for s in cls.spells if s.name != "Aspect of the Hawk"]
    assert (hunter_rotation(stats, no_hawk, cls, only(cls, "Deadly Aspects"), BOSS).auto_dps
            == pytest.approx(hunter_rotation(stats, no_hawk, cls, {}, BOSS).auto_dps))
