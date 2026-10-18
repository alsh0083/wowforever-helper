"""Retribution mana (#399): Seal of Command recast after each Judgement, Judgement, Holy Strike and the execute share
of Hammer of Wrath on cooldown, Consecration on packs; Benediction, Twist of Light, Holy Conduit and Sanctified
Judgement cut the costs, Reverence keeps 30% of Spirit regen going ((15 + Spirit / 5) per 2 s tick, Classic,
config/melee.toml [paladin]). Out of mana, Retribution swings white."""

import pytest

from wowforever.classes import class_module
from wowforever.classes.paladin_rotation import paladin_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

P = class_module("paladin")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("paladin"), P.TALENT_EFFECTS,
                               P.UNMODELED)
STATS = stat_table("paladin").at(60)
BOSS = Target(3, 0)


def spell(name):
    return best_rank(CLS.spells, name, 60)


def ranks(*names):
    return {CLS.talent_named(n).talent_id: CLS.talent_named(n).max_rank for n in names}


SOC, J, HS, HOW, CONS = (spell(n) for n in ("Seal of Command", "Judgement", "Holy Strike", "Hammer of Wrath",
                                            "Consecration"))


def test_rules():
    assert PROBLEMS == []
    expected = {
        "Reverence": ("regen_while_casting", ("all",), 30.0),
        "Benediction": ("mana_cost_pct", ("@instant",), -10.0),
        "Twist of Light": ("mana_cost_pct", ("@seal",), -20.0),
        "Holy Conduit": ("mana_cost_pct", ("Consecration", "Holy Wrath", "Exorcism", "Hammer of Wrath"), -40.0),
        "Sanctified Judgement": ("seal_refund_pct", ("Judgement",), 60.0),
    }
    for name, (kind, applies, top) in expected.items():
        (rule,) = [e for e in CLS.talent_named(name).effects if e.kind == kind]
        assert (rule.applies_to, rule.values[-1]) == (applies, top), name
    # Sanctified Judgement rank 1: a 33% chance to return 20%
    (rule,) = CLS.talent_named("Sanctified Judgement").effects
    assert rule.values[0] == pytest.approx(6.6)


def test_costs_without_mana_talents():
    r = paladin_rotation(STATS, CLS.spells, CLS, ranks("Seal of Command"), BOSS)
    expected = ((SOC.mana_cost + J.mana_cost) / J.cooldown + HS.mana_cost / HS.cooldown
                + 0.20 * HOW.mana_cost / HOW.cooldown
                + CONS.mana_cost / max(CONS.duration, CONS.cooldown))       # on one target too (#399)
    assert r.mana_per_second == pytest.approx(expected)


def test_costs_with_mana_talents():
    talents = ranks("Seal of Command", "Benediction", "Twist of Light", "Holy Conduit", "Sanctified Judgement",
                    "Reverence")
    r = paladin_rotation(STATS, CLS.spells, CLS, talents, BOSS)
    seal = SOC.mana_cost * (1 - 0.10 - 0.20) * (1 - 0.60)
    expected = ((seal + J.mana_cost * 0.9) / J.cooldown + HS.mana_cost * 0.9 / HS.cooldown
                + 0.20 * HOW.mana_cost * 0.5 / HOW.cooldown
                + CONS.mana_cost * 0.5 / max(CONS.duration, CONS.cooldown)
                - 0.30 * (15 + STATS.spirit / 5) / 2)
    assert STATS.spirit > 0
    assert r.mana_per_second == pytest.approx(expected)


def test_consecration_costs_the_same_on_packs():
    # kept down on one target too (#399), so a pack costs no extra mana
    talents = ranks("Seal of Command")
    one = paladin_rotation(STATS, CLS.spells, CLS, talents, BOSS).mana_per_second
    pack = paladin_rotation(STATS, CLS.spells, CLS, talents, BOSS, pack=3).mana_per_second
    assert pack == pytest.approx(one)


def test_output_falls_back_to_white_swings():
    talents = ranks("Seal of Command")
    r = paladin_rotation(STATS, CLS.spells, CLS, talents, BOSS)
    out = P.output(STATS, CLS.spells, CLS, talents, BOSS)
    assert out.mana_per_second == pytest.approx(r.mana_per_second) and out.mana_per_second > 0
    assert len(out.alternatives) == 1                    # without Consecration (#399)
    assert out.fallback_dps == pytest.approx(r.white_dps) and out.fallback_dps < out.dps
