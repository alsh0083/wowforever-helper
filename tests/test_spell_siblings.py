"""Holy Nova, Fire Nova and Thorns damage from the client tables (#261).

Rows are hand-made from build 1.60.1.70338's real ones (ids, base points and coefficients as in the
client); every other column takes the fixture table's header with a neutral default.
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


def _spells(trainable, other=(), effects=(), misc=()):
    """trainable/other: (id, name, BaseLevel); effects: dicts for SpellEffect; misc: dicts for SpellMisc."""
    every = list(trainable) + list(other)
    tables = {
        "SkillLineAbility": _table("SkillLineAbility", [{"Spell": i, "SkillLine": LINE, "AcquireMethod": 0}
                                                        for i, _, _ in trainable]),
        "SpellName": _table("SpellName", [{"ID": i, "Name_lang": n} for i, n, _ in every]),
        "SpellLevels": _table("SpellLevels", [{"SpellID": i, "BaseLevel": lvl, "MaxLevel": 0} for i, _, lvl in every]),
        "SpellEffect": _table("SpellEffect", [{"EffectIndex": 0, "Variance": 0, **e} for e in effects]),
        "SpellMisc": _table("SpellMisc", list(misc)),
    }
    for name in ("SpellCastTimes", "SpellCooldowns", "SpellDuration", "SpellPower", "SpellRange",
                 "SpellTargetRestrictions"):
        tables[name] = []
    return class_spells(tables, skill_lines=(LINE,))


def test_holy_nova_keeps_the_damage_spell_of_each_damage_heal_pair():
    spells = _spells(
        trainable=[(15237, "Holy Nova", 20), (23455, "Holy Nova", 20), (27801, "Holy Nova", 60), (27805, "Holy Nova", 60)],
        effects=[{"SpellID": 15237, "Effect": 2, "EffectBasePointsF": 27, "EffectBonusCoefficient": 0.107},
                 {"SpellID": 23455, "Effect": 10, "EffectBasePointsF": 52, "EffectBonusCoefficient": 0.107},
                 {"SpellID": 27801, "Effect": 2, "EffectBasePointsF": 187, "EffectBonusCoefficient": 0.107},
                 {"SpellID": 27805, "Effect": 10, "EffectBasePointsF": 311, "EffectBonusCoefficient": 0.107}])
    nova = ranks_of(spells, "Holy Nova")
    assert [(s.spell_id, s.rank, s.level) for s in nova] == [(15237, 1, 20), (27801, 2, 60)]
    assert nova[-1].min_damage == pytest.approx(187) and nova[-1].coefficient == pytest.approx(0.107)


def test_fire_nova_takes_damage_from_the_nearest_id_sibling_at_its_level():
    # 408345 is Effect 3 (dummy); at BaseLevel 52 both Classic 11307 and Forever 408428 carry the damage
    spells = _spells(
        trainable=[(408345, "Fire Nova", 52)],
        other=[(11307, "Fire Nova", 52), (408428, "Fire Nova", 52), (408427, "Fire Nova", 42)],
        effects=[{"SpellID": 408345, "Effect": 3, "EffectBasePointsF": 5},
                 {"SpellID": 11307, "Effect": 2, "EffectBasePointsF": 419, "EffectBonusCoefficient": 0.143},
                 {"SpellID": 408428, "Effect": 2, "EffectBasePointsF": 403, "EffectBonusCoefficient": 0.214},
                 {"SpellID": 408427, "Effect": 2, "EffectBasePointsF": 284, "EffectBonusCoefficient": 0.214}])
    nova = ranks_of(spells, "Fire Nova")[0]
    assert (nova.min_damage, nova.max_damage) == (pytest.approx(403), pytest.approx(403))
    assert nova.coefficient == pytest.approx(0.214)


def test_a_spell_with_its_own_damage_ignores_siblings():
    spells = _spells(
        trainable=[(585, "Smite", 1)], other=[(9999, "Smite", 1)],
        effects=[{"SpellID": 585, "Effect": 2, "EffectBasePointsF": 15, "EffectBonusCoefficient": 0.123},
                 {"SpellID": 9999, "Effect": 2, "EffectBasePointsF": 999, "EffectBonusCoefficient": 1}])
    smite = ranks_of(spells, "Smite")[0]
    assert smite.min_damage == pytest.approx(15) and smite.coefficient == pytest.approx(0.123)


def test_thorns_is_a_damage_shield():
    spells = _spells(
        trainable=[(9910, "Thorns", 54)],
        effects=[{"SpellID": 9910, "Effect": 6, "EffectAura": 15, "EffectBasePointsF": 18, "EffectBonusCoefficient": 0}])
    thorns = ranks_of(spells, "Thorns")[0]
    assert thorns.damage_shield == pytest.approx(18) and thorns.damage_shield_coefficient == 0
    assert (thorns.min_damage, thorns.periodic_damage) == (0, 0)
