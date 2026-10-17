"""Retribution's Hammer of Wrath and Champion of the Light (#399): Hammer of Wrath is usable below 20% health, so
it counts for 20% of the fight, on cooldown; Champion of the Light gives spell power from 30% of Intellect, which
Hammer of Wrath (and Consecration against a pack) use."""

import pytest

from wowforever.calc.ev import miss_chance
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
NO_HAMMER = [s for s in CLS.spells if s.name != "Hammer of Wrath"]
CHAMPION = {CLS.talent_named("Champion of the Light").talent_id: 3}


def hammer_dps(spell_power):
    hammer = best_rank(CLS.spells, "Hammer of Wrath", 60)
    hit = 1 - miss_chance(60, 63, STATS.hit_pct) / 100
    crit = min(1.0, STATS.crit_pct / 100)
    damage = (hammer.min_damage + hammer.max_damage) / 2 + hammer.coefficient * spell_power
    return 0.20 * hit * damage * (1 + crit * 0.5) / max(hammer.cooldown, 1.5)


def test_rule():
    assert PROBLEMS == []
    (rule,) = CLS.talent_named("Champion of the Light").effects
    assert (rule.kind, rule.applies_to, rule.values) == ("spell_power_from", ("intellect",), (10.0, 20.0, 30.0))


def test_hammer_of_wrath_in_the_execute_phase():
    with_hammer = paladin_rotation(STATS, CLS.spells, CLS, {}, BOSS)
    without = paladin_rotation(STATS, NO_HAMMER, CLS, {}, BOSS)
    assert "Hammer of Wrath" in with_hammer.abilities
    assert with_hammer.dps - without.dps == pytest.approx(hammer_dps(0.0))


def test_champion_of_the_light_powers_the_hammer():
    gain = (paladin_rotation(STATS, CLS.spells, CLS, CHAMPION, BOSS).dps
            - paladin_rotation(STATS, NO_HAMMER, CLS, CHAMPION, BOSS).dps)
    assert gain == pytest.approx(hammer_dps(0.30 * STATS.intellect))
