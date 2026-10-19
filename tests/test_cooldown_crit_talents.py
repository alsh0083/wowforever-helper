"""Rapid Killing (#393: Rapid Fire's cooldown 2 min shorter) and Holy Power (#399: +15% crit on Holy Strike)."""

import pytest

from wowforever.classes import class_module
from wowforever.classes.hunter_rotation import hunter_rotation
from wowforever.classes.paladin_rotation import paladin_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
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


@pytest.mark.parametrize("name", ["hunter", "paladin"])
def test_rules_parse(name):
    assert loaded(name)[1] == []


def test_rapid_killing_shortens_rapid_fire():
    cls, _ = loaded("hunter")
    (rule,) = cls.talent_named("Rapid Killing").effects
    assert (rule.kind, rule.applies_to, rule.values) == ("cooldown", ("Rapid Fire",), (-60.0, -120.0))
    stats = stat_table("hunter").at(60)
    rapid = best_rank(cls.spells, "Rapid Fire", 60)              # +40% for 15 s every 300 s
    base = hunter_rotation(stats, cls.spells, cls, {}, BOSS)
    quick = hunter_rotation(stats, cls.spells, cls, only(cls, "Rapid Killing"), BOSS)
    share = rapid.haste_pct / 100 * rapid.duration
    assert quick.auto_dps == pytest.approx(base.auto_dps * (1 + share / (rapid.cooldown - 120))
                                           / (1 + share / rapid.cooldown))


def test_holy_power_crit_on_holy_strike():
    cls, _ = loaded("paladin")
    rule = next(e for e in cls.talent_named("Holy Power").effects if e.kind == "crit_chance")
    assert set(rule.applies_to) == {"Holy Strike", "Holy Shock"} and rule.values[-1] == 15
    stats = stat_table("paladin").at(60)
    base = paladin_rotation(stats, cls.spells, cls, {}, BOSS)
    holy = paladin_rotation(stats, cls.spells, cls, only(cls, "Holy Power"), BOSS)
    assert holy.dps > base.dps
