"""Shank in the client tables (#470): on a rogue skill line with BaseLevel 0 (learned at SpellLevel 24 and 44), a
percent-weapon effect alone (31: 50%) and an energize of power type 3 (15 and 25 Energy)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "data" / "cache" / "hotfixed" / "1.60.1.70755-20261103"


@pytest.mark.skipif(not TABLES.is_dir(), reason="client tables not cached")
def test_class_spells_reads_shank():
    from wowforever.classes import class_module
    from wowforever.normalize import read_tables
    from wowforever.normalize_spells import class_spells

    rogue = class_module("rogue")
    spells = class_spells(read_tables(TABLES), skill_lines=rogue.SKILL_LINES, extra_spells=rogue.EXTRA_SPELLS)
    shank = [(s.spell_id, s.rank, s.level, s.energy_cost, s.energy_gain, s.cooldown, s.weapon_pct, s.weapon_hits)
             for s in spells if s.name == "Shank"]
    assert shank == [(1329283, 1, 24, 5, 15, 10.0, 50.0, 1), (1329549, 2, 44, 5, 25, 10.0, 50.0, 1)]


def test_spell_ranks_carry_energy_gained():
    from wowforever.schema import SpellRank

    assert SpellRank(1, "x", 1, 1, ("physical",), 0.0).energy_gain == 0
