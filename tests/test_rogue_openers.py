"""Questing openers (#431): damage dealt once per kill on top of the rotation, which questing takes off the mob's
health (`Output.opener_damage`).

Rogue: with a dagger (the Backstab run) each fight opens with Ambush from stealth in place of the first builder;
Initiative's chance of an extra combo point saves a builder. Remorseless Attacks (+20% / +40% crit on the next
Sinister Strike, Backstab or Ambush after a kill) boosts the first attack of the next fight: Ambush when opening
with it, otherwise the builder."""

import pytest

from wowforever import melee_scenarios as ms
from wowforever.classes import class_module
from wowforever.classes.rogue_rotation import rogue_rotation
from wowforever.effects import attach_effects
from wowforever.physical import Attacker, Target, yellow_attack
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

R = class_module("rogue")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("rogue"), R.TALENT_EFFECTS,
                               R.UNMODELED)
STATS = ms.stat_table("rogue").at(60)
MOB = Target(0, 3000)
REMORSELESS = CLS.talent_named("Remorseless Attacks").talent_id
INITIATIVE = CLS.talent_named("Initiative").talent_id


def hit(stats, name, speed, extra_crit=0.0):
    spell = best_rank(CLS.spells, name, 60)
    mn, mx, _ = stats.main_hand
    scale = spell.weapon_pct / 100 if spell.weapon_pct else 1
    base = ((mn + mx) / 2 + stats.attack_power / 14 * speed + spell.weapon_bonus) * scale
    return yellow_attack(base, Attacker(60, stats.attack_power, stats.crit_pct, stats.hit_pct), MOB,
                         crit_bonus=extra_crit)


def test_rules():
    assert PROBLEMS == []
    (rule,) = CLS.talent_named("Remorseless Attacks").effects
    assert (rule.kind, rule.applies_to, rule.values) == ("crit_chance", ("@after_kill",), (20.0, 40.0))
    (rule,) = CLS.talent_named("Initiative").effects
    assert (rule.kind, rule.applies_to, rule.values[-1]) == ("proc_chance", ("@initiative",), 100.0)


def test_no_opener_without_the_talents_or_a_dagger():
    assert rogue_rotation(STATS, CLS.spells, CLS, {}, MOB).opener_damage == 0.0


def test_remorseless_boosts_the_first_builder():
    r = rogue_rotation(STATS, CLS.spells, CLS, {REMORSELESS: 2}, MOB)
    assert r.builder == "Sinister Strike"
    plain, boosted = hit(STATS, "Sinister Strike", 2.4), hit(STATS, "Sinister Strike", 2.4, 40.0)
    assert r.opener_damage == pytest.approx(boosted - plain)


def test_ambush_opens_with_a_dagger():
    stats = R.dagger(STATS)
    r = rogue_rotation(stats, CLS.spells, CLS, {REMORSELESS: 2, INITIATIVE: 3}, MOB, backstab=True)
    assert r.builder == "Backstab"
    backstab = hit(stats, "Backstab", 1.7)
    # Ambush with Remorseless' crit replaces the first Backstab; Initiative's extra combo point saves another
    assert r.opener_damage == pytest.approx(hit(stats, "Ambush", 1.7, 40.0) - backstab + 1.0 * backstab)


def test_questing_takes_the_opener_off_the_mob():
    # 1500 HP mob, 500 opener damage, 100 DPS: 10 s to kill; no eating or drinking, 12 s travel: 3600 / 22
    class Q:
        mob_hp, drink_mana_per_second, travel_seconds = 1500.0, 100.0, 12.0

    out = ms.Output(100.0, 0.0, 100.0, pet=True, opener_damage=500.0)
    assert ms.questing_kills_per_hour(out, Q, 10.0, 50.0) == pytest.approx(3600 / 22)
    # an opener bigger than the mob: the kill takes no time
    big = ms.Output(100.0, 0.0, 100.0, pet=True, opener_damage=5000.0)
    assert ms.questing_kills_per_hour(big, Q, 10.0, 50.0) == pytest.approx(3600 / 12)


def test_rogue_output_carries_the_opener():
    talents = {REMORSELESS: 2}
    out = R.output(STATS, CLS.spells, CLS, talents, MOB)
    assert out.opener_damage > 0
