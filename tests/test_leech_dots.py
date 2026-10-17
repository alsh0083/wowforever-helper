"""Leech DoTs (#382).

Devouring Plague, Siphon Life and Drain Life apply aura 53 (periodic leech: the target takes the damage and the
caster is healed) instead of aura 3. Devouring Plague rank 6 (19280, 70425 client tables): aura 53, 106 every
3000 ms, coefficient 0.1 per tick, 24 s duration, so 8 ticks: periodic 106 x 8 = 848, coefficient 0.1 x 8 = 0.8.
Rows are hand-made from the 70425 client tables.
"""

import csv
from pathlib import Path

import pytest

from wowforever.normalize_spells import class_spells, ranks_of

FIXTURE = Path(__file__).parent / "fixtures" / "wago-1.60.1.70205-spells"
LINE = 78   # any skill line the test asks for


def _table(name, rows):
    with (FIXTURE / f"{name}.csv").open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    return [{col: str(row.get(col, "0")) for col in header} for row in rows]


def _tables(aura):
    tables = {
        "SkillLineAbility": _table("SkillLineAbility", [{"Spell": 19280, "SkillLine": LINE, "AcquireMethod": 0}]),
        "SpellName": _table("SpellName", [{"ID": 19280, "Name_lang": "Devouring Plague"}]),
        "SpellLevels": _table("SpellLevels", [{"SpellID": 19280, "BaseLevel": 60, "MaxLevel": 0}]),
        "SpellEffect": _table("SpellEffect", [
            {"SpellID": 19280, "EffectIndex": 0, "Effect": 6, "EffectAura": aura, "EffectBasePointsF": 106,
             "EffectAuraPeriod": 3000, "EffectBonusCoefficient": 0.1}]),
        "SpellMisc": _table("SpellMisc", [{"SpellID": 19280, "DurationIndex": 106, "SchoolMask": 32}]),
        "SpellDuration": _table("SpellDuration", [{"ID": 106, "Duration": 24000, "MaxDuration": 24000}]),
    }
    for name in ("SpellCastTimes", "SpellCooldowns", "SpellPower", "SpellRange", "SpellTargetRestrictions"):
        tables[name] = []
    return tables


@pytest.mark.parametrize("aura", [53, 3])
def test_leech_and_plain_dots_read_the_same_periodic_damage(aura):
    plague = ranks_of(class_spells(_tables(aura), skill_lines=(LINE,)), "Devouring Plague")[0]
    assert plague.tick_period == 3.0
    assert plague.periodic_damage == pytest.approx(848)
    assert plague.periodic_coefficient == pytest.approx(0.8)
