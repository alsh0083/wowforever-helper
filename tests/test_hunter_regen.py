"""Hunter mana regen while casting (#393 part B): Bestial Discipline (50%) and Rapid Recuperation (50% while Serpent
Sting is up) keep that share of Spirit regen going; regen per second = (15 + Spirit / 5) / 2 (Classic, per 2 s
tick; config/melee.toml [hunter])."""

import pytest

from wowforever.classes import class_module
from wowforever.classes.hunter_rotation import hunter_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path

H = class_module("hunter")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("hunter"), H.TALENT_EFFECTS,
                               H.UNMODELED)
STATS = stat_table("hunter").at(60)
BOSS = Target(3, 0)


def only(name):
    return {CLS.talent_named(name).talent_id: 2}


def test_rules():
    assert PROBLEMS == []
    for name, token in (("Bestial Discipline", "all"), ("Rapid Recuperation", "@sting")):
        (rule,) = [e for e in CLS.talent_named(name).effects if e.kind == "regen_while_casting"]
        assert (rule.applies_to, rule.values) == ((token,), (25.0, 50.0)), name


@pytest.mark.parametrize("talent", ["Bestial Discipline", "Rapid Recuperation"])
def test_half_the_spirit_regen_while_casting(talent):
    base = hunter_rotation(STATS, CLS.spells, CLS, {}, BOSS)
    regen = (15 + STATS.spirit / 5) / 2
    assert STATS.spirit > 0
    with_talent = hunter_rotation(STATS, CLS.spells, CLS, only(talent), BOSS)
    assert base.mode == with_talent.mode == "ranged"
    assert with_talent.mana_per_second == pytest.approx(base.mana_per_second - 0.5 * regen)


def test_rapid_recuperation_needs_serpent_sting():
    no_sting = [s for s in CLS.spells if s.name != "Serpent Sting"]
    assert (hunter_rotation(STATS, no_sting, CLS, only("Rapid Recuperation"), BOSS).mana_per_second
            == pytest.approx(hunter_rotation(STATS, no_sting, CLS, {}, BOSS).mana_per_second))
