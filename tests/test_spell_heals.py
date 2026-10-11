"""Direct and periodic heals from the client tables (#270). Rows as in build 1.60.1.70291.

Hand-worked: Regrowth rank 9 lasts 21 s with a 3 s tick: 7 ticks x 142 = 994 healing over time,
coefficient 7 x 0.071 = 0.497; its direct part is 1021 (variance 0 here), coefficient 0.286.
Rejuvenation rank 11 lasts 12 s: 4 ticks x 194 = 776, coefficient 4 x 0.2 = 0.8.
Tranquility rank 5 (Effect 35 area aura) lasts 8 s at 2 s: 4 ticks x 285 = 1140, coefficient 4 x 0.067 = 0.268.
"""

import pytest

from test_spell_siblings import _spells, _table  # the hand-made table helper (#261)
from wowforever.normalize_spells import ranks_of


def _heal_spells(trainable, effects, durations):
    import wowforever.normalize_spells as ns
    from test_spell_siblings import LINE
    every = list(trainable)
    misc = [{"SpellID": i, "DurationIndex": 100 + k} for k, i in enumerate(durations)]
    tables = {
        "SkillLineAbility": _table("SkillLineAbility", [{"Spell": i, "SkillLine": LINE, "AcquireMethod": 0} for i, _, _ in every]),
        "SpellName": _table("SpellName", [{"ID": i, "Name_lang": n} for i, n, _ in every]),
        "SpellLevels": _table("SpellLevels", [{"SpellID": i, "BaseLevel": lvl, "MaxLevel": 0} for i, _, lvl in every]),
        "SpellEffect": _table("SpellEffect", [{"EffectIndex": 0, "Variance": 0, **e} for e in effects]),
        "SpellMisc": _table("SpellMisc", misc),
        "SpellDuration": _table("SpellDuration", [{"ID": 100 + k, "Duration": int(s * 1000)} for k, s in enumerate(durations.values())]),
    }
    for name in ("SpellCastTimes", "SpellCooldowns", "SpellPower", "SpellRange", "SpellTargetRestrictions"):
        tables[name] = []
    return ns.class_spells(tables, skill_lines=(LINE,))


SPELLS = _heal_spells(
    trainable=[(25297, "Healing Touch", 60), (9858, "Regrowth", 60), (25299, "Rejuvenation", 60), (9863, "Tranquility", 60),
               (9912, "Wrath", 54)],
    effects=[{"SpellID": 25297, "Effect": 10, "EffectBasePointsF": 2332, "EffectBonusCoefficient": 1.0},
             {"SpellID": 9858, "Effect": 10, "EffectBasePointsF": 1021, "EffectBonusCoefficient": 0.286},
             {"SpellID": 9858, "EffectIndex": 1, "Effect": 6, "EffectAura": 8, "EffectBasePointsF": 142,
              "EffectBonusCoefficient": 0.071, "EffectAuraPeriod": 3000},
             {"SpellID": 25299, "Effect": 6, "EffectAura": 8, "EffectBasePointsF": 194, "EffectBonusCoefficient": 0.2,
              "EffectAuraPeriod": 3000},
             {"SpellID": 9863, "Effect": 35, "EffectAura": 8, "EffectBasePointsF": 285, "EffectBonusCoefficient": 0.067,
              "EffectAuraPeriod": 2000},
             {"SpellID": 9912, "Effect": 2, "EffectBasePointsF": 91, "EffectBonusCoefficient": 0.571}],
    durations={9858: 21, 25299: 12, 9863: 8})


def one(name):
    return ranks_of(SPELLS, name)[0]


def test_direct_heal():
    ht = one("Healing Touch")
    assert (ht.heal_min, ht.heal_max, ht.heal_coefficient) == (pytest.approx(2332), pytest.approx(2332), pytest.approx(1.0))
    assert ht.periodic_heal == 0 and ht.min_damage == 0


def test_direct_plus_periodic_heal():
    rg = one("Regrowth")
    assert rg.heal_min == pytest.approx(1021) and rg.heal_coefficient == pytest.approx(0.286)
    assert rg.periodic_heal == pytest.approx(994) and rg.periodic_heal_coefficient == pytest.approx(0.497)


def test_heal_over_time_only():
    rj = one("Rejuvenation")
    assert rj.heal_min == 0
    assert rj.periodic_heal == pytest.approx(776) and rj.periodic_heal_coefficient == pytest.approx(0.8)


def test_area_aura_heal_over_time():
    tq = one("Tranquility")
    assert tq.periodic_heal == pytest.approx(1140) and tq.periodic_heal_coefficient == pytest.approx(0.268)


def test_damage_spells_carry_no_healing():
    wrath = one("Wrath")
    assert (wrath.heal_min, wrath.periodic_heal) == (0, 0) and wrath.min_damage == pytest.approx(91)
