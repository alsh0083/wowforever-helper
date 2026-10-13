"""Consecration's tick damage (#295).

Forever's Consecration (20924 at rank 5) is a dummy with an area trigger and an area-periodic marker
(aura 226, 1 s period, 8 s). Its tick damage sits in the non-trainable same-name spell at its level
(1280349), which has two Effect 2 rows with the same targets (ImplicitTarget 87/16, radius 14): 12 base
(coefficient 0) and 27 base (coefficient 0.095). Both hit, so a tick deals 39 + 0.095 x spell power:
periodic 39 x 8 = 312, coefficient 0.095 x 8 = 0.76. Rows are hand-made from the 70291 client tables.
"""

import csv
from pathlib import Path

import pytest

from wowforever.normalize_spells import class_spells, ranks_of

FIXTURE = Path(__file__).parent / "fixtures" / "wago-1.60.1.70205-spells"
LINE = 594   # any skill line the test asks for


def _table(name, rows):
    with (FIXTURE / f"{name}.csv").open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    return [{col: str(row.get(col, "0")) for col in header} for row in rows]


def test_consecration_ticks_with_both_damage_effects():
    trainable, other = [(20924, "Consecration", 60)], [(1280349, "Consecration", 60)]
    every = trainable + other
    tables = {
        "SkillLineAbility": _table("SkillLineAbility", [{"Spell": 20924, "SkillLine": LINE, "AcquireMethod": 0}]),
        "SpellName": _table("SpellName", [{"ID": i, "Name_lang": n} for i, n, _ in every]),
        "SpellLevels": _table("SpellLevels", [{"SpellID": i, "BaseLevel": lvl, "MaxLevel": 0} for i, _, lvl in every]),
        "SpellEffect": _table("SpellEffect", [
            {"SpellID": 20924, "EffectIndex": 0, "Effect": 3, "EffectBasePointsF": 30},
            {"SpellID": 20924, "EffectIndex": 1, "Effect": 179, "EffectMiscValue_0": 41316},
            {"SpellID": 20924, "EffectIndex": 2, "Effect": 6, "EffectAura": 226, "EffectBasePointsF": 4,
             "EffectAuraPeriod": 1000},
            {"SpellID": 1280349, "EffectIndex": 0, "Effect": 2, "EffectBasePointsF": 12, "EffectBonusCoefficient": 0},
            {"SpellID": 1280349, "EffectIndex": 1, "Effect": 2, "EffectBasePointsF": 27,
             "EffectBonusCoefficient": 0.095}]),
        "SpellMisc": _table("SpellMisc", [{"SpellID": 20924, "DurationIndex": 9, "SchoolMask": 2}]),
        "SpellDuration": _table("SpellDuration", [{"ID": 9, "Duration": 8000, "MaxDuration": 8000}]),
    }
    for name in ("SpellCastTimes", "SpellCooldowns", "SpellPower", "SpellRange", "SpellTargetRestrictions"):
        tables[name] = []
    consecration = ranks_of(class_spells(tables, skill_lines=(LINE,)), "Consecration")[0]
    assert consecration.tick_period == 1.0
    assert consecration.periodic_damage == pytest.approx(312)
    assert consecration.periodic_coefficient == pytest.approx(0.76)
