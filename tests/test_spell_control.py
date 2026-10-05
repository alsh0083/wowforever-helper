"""Survival and control fields on spell ranks (#25), from the real fixture spell tables.
Values were read off the fixture rows: Ice Barrier r1 absorbs 431 (60 s), Mana Shield r1 120,
Frost Nova roots for 8 s, Ice Block is 10 s immunity, Polymorph r4 lasts 50 s, Counterspell
locks out for 10 s."""

from pathlib import Path

import pytest

from wowforever.normalize import read_tables
from wowforever.normalize_spells import class_spells, ranks_of

SPELLS = class_spells(read_tables(Path(__file__).parent / "fixtures" / "wago-1.60.1.70205-spells"),
                      skill_lines=(6, 8, 237))


def first(name):
    return ranks_of(SPELLS, name)[0]


def test_absorbs():
    assert ranks_of(SPELLS, "Ice Barrier")[0].absorb == pytest.approx(431)
    assert first("Mana Shield").absorb == pytest.approx(120)
    assert first("Fire Ward").absorb == pytest.approx(162)
    assert first("Frostbolt").absorb == 0


def test_root_immunity_incapacitate_interrupt():
    assert first("Frost Nova").root == pytest.approx(8.0)
    block = first("Ice Block")
    assert block.immunity == pytest.approx(10.0) and block.stun == 0     # its self-stun isn't a stun on the target
    assert ranks_of(SPELLS, "Polymorph")[3].incapacitate == pytest.approx(50.0)
    assert first("Counterspell").interrupt_lockout == pytest.approx(10.0)


def test_damage_spells_carry_no_control_fields_by_accident():
    fb = first("Fireball")
    assert (fb.root, fb.stun, fb.immunity, fb.incapacitate, fb.interrupt_lockout) == (0, 0, 0, 0, 0)
