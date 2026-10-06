"""Warrior rage costs (#162, part 1): SpellPower rows with PowerType 1 carry rage in tenths."""

from pathlib import Path

from wowforever.classes import class_module
from wowforever.normalize import read_tables
from wowforever.normalize_spells import class_spells
from wowforever.schema import SpellRank

FIX = Path(__file__).parent / "fixtures"


def spells(name):
    return {s.name: s for s in class_spells(read_tables(FIX / f"wago-1.60.1.70205-{name}"),
                                            skill_lines=class_module(name).SKILL_LINES)}


def test_warrior_abilities_carry_rage_costs():
    w = spells("warrior")
    assert (w["Mortal Strike"].rage_cost, w["Heroic Strike"].rage_cost, w["Whirlwind"].rage_cost) == (30, 15, 25)
    assert (w["Overpower"].rage_cost, w["Execute"].rage_cost, w["Bloodthirst"].rage_cost) == (5, 15, 30)
    assert w["Mortal Strike"].mana_cost == 0 and w["Mortal Strike"].energy_cost == 0


def test_other_classes_have_no_rage_costs():
    assert all(s.rage_cost == 0 for s in spells("rogue").values())
    assert spells("rogue")["Kick"].energy_cost == 25


def test_rage_cost_defaults_to_zero():
    assert SpellRank.__dataclass_fields__["rage_cost"].default == 0
