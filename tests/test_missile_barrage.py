"""Missile Barrage (#394): a proc makes the next Arcane Missiles half as long and free.

With Arcane Missiles as the filler, each landed missile can proc it, so a share q = 1 - (1 - hit x chance)^missiles
of the casts are barrages: casts average (1 - q / 2) of the channel and (1 - q) of the mana. With Fireball,
Frostbolt, Frostfire Bolt or Arcane Wrath as the filler, each landed cast can proc it, and the mage weaves in a free
half-length Arcane Missiles when that beats the filler time it takes."""

import pytest

from wowforever.assumptions import Assumptions, periodic_can_crit, sub20_penalized
from wowforever.calc.ev import effective_cast_time, expected_damage, miss_chance
from wowforever.calc.talents import modifiers_for
from wowforever.classes import class_module
from wowforever.classes.mage_rotation import missile_barrage_rule, rotation
from wowforever.effects import attach_effects
from wowforever.scenarios import Character, best_rank, scaled
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.stats import Stats

M = class_module("mage")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("mage"), M.TALENT_EFFECTS, M.UNMODELED)
STATS = Stats(60, intellect=270, spirit=190, stamina=220, spell_power=150, crit_pct=6, hit_pct=3,
              mana=3600, health=2900)
A = Assumptions.load().with_values(level_resistance=False)   # pins the formula; resistance: #409
SUSTAINED = frozenset({"sustained"})
MB = CLS.talent_named("Missile Barrage").talent_id


def spell(name):
    return best_rank(CLS.spells, name, 60)


def run(rank, filler):
    return rotation(Character(60, STATS, CLS.spells, CLS, {MB: rank} if rank else {}), spell(filler),
                    target_level=63, assumptions=A, sustained=True)


def ev(s, mods):
    return expected_damage(sub20_penalized(scaled(s, 60), A), spell_power=150, crit_pct=6, hit_pct=3,
                           caster_level=60, target_level=63, mods=mods,
                           periodic_can_crit=periodic_can_crit(s.name, A))


def hit_of(s):
    return 1 - miss_chance(60, 63, 3 + modifiers_for(s, CLS, {}, SUSTAINED).hit_bonus) / 100


def test_rule_per_rank():
    assert missile_barrage_rule(CLS, 2) == {"Arcane Blast": 40.0, "Arcane Missiles": 10.0, "Arcane Wrath": 20.0,
                                            "Fireball": 20.0, "Frostbolt": 20.0, "Frostfire Bolt": 20.0}
    assert missile_barrage_rule(CLS, 1)["Arcane Missiles"] == 5.0


def test_arcane_missiles_filler():
    am = spell("Arcane Missiles")
    missiles = round(am.duration / am.tick_period)
    assert missiles == 5
    q = 1 - (1 - hit_of(am) * 0.10) ** missiles
    base, barrage = run(0, "Arcane Missiles"), run(2, "Arcane Missiles")
    assert barrage.dps / base.dps == pytest.approx(1 / (1 - q / 2))
    assert barrage.mana_per_second / base.mana_per_second == pytest.approx((1 - q) / (1 - q / 2))


def test_frostbolt_weaves_a_free_barrage():
    fb, am = spell("Frostbolt"), spell("Arcane Missiles")
    fmods, amods = modifiers_for(fb, CLS, {}, SUSTAINED), modifiers_for(am, CLS, {}, SUSTAINED)
    cast = effective_cast_time(fb, fmods)
    n = 60 / cast * hit_of(fb) * 0.20                    # barrages per minute
    base, barrage = run(0, "Frostbolt"), run(2, "Frostbolt")
    assert barrage.weaves["Arcane Missiles"] == pytest.approx(n)
    gain = ev(am, amods) - ev(fb, fmods) / cast * am.duration / 2
    assert gain > 0
    assert barrage.dps - base.dps == pytest.approx(n * gain / 60)
    # a barrage is free, and the filler casts less for the time it takes
    assert barrage.mana_per_second == pytest.approx(base.mana_per_second * (1 - n * am.duration / 2 / 60))
