"""Hunter traps: one rank per trap, with its effect's damage (#268).

A trap is two trainable spells at each level (build 1.60.1.70291): the trap you place (only Effect 104,
summon a trap object; it has the mana cost) and the effect that deals the damage, named like the trap
(Immolation Trap, 70291) or "<trap> Effect" (Explosive Trap Effect). They become one rank: the placed
spell, carrying the effect's damage fields (direct damage, periodic damage, tick period, duration,
schools). The effect spell is no longer a rank of its own. A buff trained beside its damage proc
(Lightning Shield) isn't a trap and keeps both ranks (#261).

Rows are hand-made from the 70291 client tables:
  Immolation Trap rank 1: 13795 (Effect 104, 50 mana) + 13797 (aura 3, 21 per 3 s for 15 s = 105)
  Explosive Trap rank 1: 13813 (Effect 104) + 13812 "Explosive Trap Effect" (Effect 2, 115 base)
"""

import csv
from pathlib import Path

import pytest

from wowforever.normalize_spells import class_spells, ranks_of

FIXTURE = Path(__file__).parent / "fixtures" / "wago-1.60.1.70205-spells"
LINE = 51   # hunter's Survival skill line


def _table(name, rows):
    with (FIXTURE / f"{name}.csv").open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    return [{col: str(row.get(col, "0")) for col in header} for row in rows]


def _spells(trainable, effects, misc=(), durations=(), powers=()):
    """trainable: (id, name, BaseLevel); effects: SpellEffect dicts; misc/durations/powers: table dicts."""
    tables = {
        "SkillLineAbility": _table("SkillLineAbility", [{"Spell": i, "SkillLine": LINE, "AcquireMethod": 0}
                                                        for i, _, _ in trainable]),
        "SpellName": _table("SpellName", [{"ID": i, "Name_lang": n} for i, n, _ in trainable]),
        "SpellLevels": _table("SpellLevels", [{"SpellID": i, "BaseLevel": lvl, "MaxLevel": 0} for i, _, lvl in trainable]),
        "SpellEffect": _table("SpellEffect", [{"EffectIndex": 0, "Variance": 0, **e} for e in effects]),
        "SpellMisc": _table("SpellMisc", list(misc)),
        "SpellDuration": _table("SpellDuration", list(durations)),
        "SpellPower": _table("SpellPower", list(powers)),
    }
    for name in ("SpellCastTimes", "SpellCooldowns", "SpellRange", "SpellTargetRestrictions"):
        tables[name] = []
    return class_spells(tables, skill_lines=(LINE,))


IMMOLATION = dict(
    trainable=[(13795, "Immolation Trap", 16), (13797, "Immolation Trap", 16)],
    effects=[{"SpellID": 13795, "Effect": 104, "EffectMiscValue_0": 164638, "EffectBonusCoefficient": 1},
             {"SpellID": 13797, "Effect": 6, "EffectAura": 3, "EffectBasePointsF": 21, "EffectAuraPeriod": 3000}],
    misc=[{"SpellID": 13797, "DurationIndex": 9, "SchoolMask": 4}],
    durations=[{"ID": 9, "Duration": 15000, "MaxDuration": 15000}],
    powers=[{"SpellID": 13795, "PowerType": 0, "ManaCost": 50}],
)


def test_immolation_trap_is_one_rank_with_its_effects_damage():
    ranks = ranks_of(_spells(**IMMOLATION), "Immolation Trap")
    assert [(s.spell_id, s.rank, s.level) for s in ranks] == [(13795, 1, 16)]
    trap = ranks[0]
    assert trap.mana_cost == 50
    assert (trap.periodic_damage, trap.tick_period, trap.duration) == (pytest.approx(105), 3.0, 15.0)
    assert trap.schools == ("fire",)


def test_explosive_trap_takes_damage_from_its_effect_spell():
    spells = _spells(
        trainable=[(13813, "Explosive Trap", 34), (13812, "Explosive Trap Effect", 34)],
        effects=[{"SpellID": 13813, "Effect": 104, "EffectMiscValue_0": 164839, "EffectBonusCoefficient": 1},
                 {"SpellID": 13812, "Effect": 2, "EffectBasePointsF": 115}])
    trap = ranks_of(spells, "Explosive Trap")
    assert [(s.spell_id, s.rank) for s in trap] == [(13813, 1)]
    assert (trap[0].min_damage, trap[0].max_damage) == (pytest.approx(115), pytest.approx(115))
    assert ranks_of(spells, "Explosive Trap Effect") == []


def test_a_trap_without_an_effect_spell_stays_as_it_is():
    spells = _spells(trainable=[(1499, "Freezing Trap", 20)],
                     effects=[{"SpellID": 1499, "Effect": 104, "EffectMiscValue_0": 2561, "EffectBonusCoefficient": 1}])
    assert [(s.spell_id, s.min_damage, s.periodic_damage) for s in ranks_of(spells, "Freezing Trap")] == [(1499, 0, 0)]


def test_a_buff_beside_its_damage_proc_is_not_a_trap():
    spells = _spells(
        trainable=[(324, "Lightning Shield", 8), (26364, "Lightning Shield", 8)],
        effects=[{"SpellID": 324, "Effect": 6, "EffectAura": 42, "EffectBasePointsF": 1},
                 {"SpellID": 26364, "Effect": 2, "EffectBasePointsF": 13, "EffectBonusCoefficient": 0.33}])
    assert [s.spell_id for s in ranks_of(spells, "Lightning Shield")] == [324, 26364]
