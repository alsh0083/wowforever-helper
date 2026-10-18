"""Combustion and Presence of Mind (#394), averaged over their cooldowns in the sustained mage rotation.

Combustion: each Fire cast raises the Fire crit chance by `step` until `limit` crits; its value is the expected
extra crit chance summed over the casts while it lasts, times the damage one crit adds, once per cooldown.
Presence of Mind: once per cooldown one cast is instant, so it takes a GCD of filler time instead of its cast time;
the mage spends it on the filler or on Pyroblast when taken, whichever gains more."""

from dataclasses import replace

import pytest

from wowforever.assumptions import Assumptions, periodic_can_crit, sub20_penalized
from wowforever.calc.ev import GCD_SECONDS, effective_cast_time, expected_damage, miss_chance
from wowforever.calc.talents import modifiers_for
from wowforever.classes import class_module
from wowforever.classes.mage_rotation import combustion_extra_crits, combustion_rule, rotation
from wowforever.effects import attach_effects
from wowforever.scenarios import Character, best_rank, scaled
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.stats import Stats

M = class_module("mage")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("mage"), M.TALENT_EFFECTS, M.UNMODELED)
STATS = Stats(60, intellect=270, spirit=190, stamina=220, spell_power=150, crit_pct=6, hit_pct=3,
              mana=3600, health=2900)
A = Assumptions.load()
SUSTAINED = frozenset({"sustained"})


def spell(name):
    return best_rank(CLS.spells, name, 60)


def ranks(*names):
    return {CLS.talent_named(n).talent_id: 1 for n in names}


def run(names, filler, sustained=True):
    return rotation(Character(60, STATS, CLS.spells, CLS, ranks(*names)), spell(filler), target_level=63,
                    assumptions=A, sustained=sustained)


def ev(s, mods):
    return expected_damage(sub20_penalized(scaled(s, 60), A), spell_power=150, crit_pct=6, hit_pct=3,
                           caster_level=60, target_level=63, mods=mods,
                           periodic_can_crit=periodic_can_crit(s.name, A))


def test_combustion_extra_crits_by_hand():
    # limit 1, step 50%, base 0: cast 0 adds 0; cast 1 is always reached and adds 0.5; cast 2 is reached when
    # cast 1 didn't crit (0.5) and adds 1.0 x 0.5; then it has always ended. 0 + 0.5 + 0.5 = 1.0
    assert combustion_extra_crits(0.0, 1.0, 0.5, 1) == pytest.approx(1.0)
    # a miss doesn't end it and doesn't count: limit 1, step 100%, hit 50%: cast 0 adds 0; every later cast adds
    # 1.0 while it lasts, and it lasts to cast k >= 1 with chance 0.5^(k-1): 1 + 0.5 + 0.25 + ... = 2.0
    assert combustion_extra_crits(0.0, 0.5, 1.0, 1) == pytest.approx(2.0)
    # crit chance caps at 1: base 0.95, step 0.1, limit 1: cast 1 is reached with 0.05 and adds 0.05
    assert combustion_extra_crits(0.95, 1.0, 0.1, 1) == pytest.approx(0.05 * 0.05)


def test_combustion_rule_from_rank_text():
    assert combustion_rule(CLS) == (10.0, 3)


def test_combustion_once_per_cooldown():
    fb = spell("Fireball")
    base, with_c = run([], "Fireball"), run(["Combustion"], "Fireball")
    mods = modifiers_for(fb, CLS, {}, SUSTAINED)
    p = (6 + mods.crit_chance_bonus) / 100
    hit = 1 - miss_chance(60, 63, 3 + mods.hit_bonus) / 100
    per_crit = (ev(fb, replace(mods, crit_chance_bonus=mods.crit_chance_bonus + 1)) - ev(fb, mods)) / 0.01
    cooldown = spell("Combustion").cooldown
    assert with_c.dps - base.dps == pytest.approx(combustion_extra_crits(p, hit, 0.10, 3) * per_crit / cooldown)
    assert with_c.dps > base.dps


def test_combustion_needs_a_fire_filler_and_a_long_fight():
    assert run(["Combustion"], "Frostbolt").dps == pytest.approx(run([], "Frostbolt").dps)
    assert (run(["Combustion"], "Fireball", sustained=False).dps
            == pytest.approx(run([], "Fireball", sustained=False).dps))


def test_presence_of_mind_on_the_filler():
    fb = spell("Frostbolt")
    base, with_pom = run([], "Frostbolt"), run(["Presence of Mind"], "Frostbolt")
    mods = modifiers_for(fb, CLS, {}, SUSTAINED)
    filler_dps = ev(fb, mods) / effective_cast_time(fb, mods)
    cooldown = spell("Presence of Mind").cooldown
    assert with_pom.dps - base.dps == pytest.approx((ev(fb, mods) - filler_dps * GCD_SECONDS) / cooldown)
    assert with_pom.mana_per_second - base.mana_per_second == pytest.approx(
        fb.mana_cost * (1 + mods.mana_cost_pct / 100) / cooldown)


def test_presence_of_mind_pyroblast():
    fb, pyro = spell("Fireball"), spell("Pyroblast")
    base, with_pom = run(["Pyroblast"], "Fireball"), run(["Pyroblast", "Presence of Mind"], "Fireball")
    talents = ranks("Pyroblast")
    fmods, pmods = modifiers_for(fb, CLS, talents, SUSTAINED), modifiers_for(pyro, CLS, talents, SUSTAINED)
    filler_dps = ev(fb, fmods) / effective_cast_time(fb, fmods)
    gain = max(ev(fb, fmods), ev(pyro, pmods)) - filler_dps * GCD_SECONDS
    assert ev(pyro, pmods) > ev(fb, fmods)
    assert with_pom.dps - base.dps == pytest.approx(gain / spell("Presence of Mind").cooldown)


def test_presence_of_mind_needs_a_long_fight():
    assert (run(["Presence of Mind"], "Frostbolt", sustained=False).dps
            == pytest.approx(run([], "Frostbolt", sustained=False).dps))
