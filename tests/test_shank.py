"""Shank (#470, 1.60.1.70755 hotfixes): every rogue's off-hand strike. Hand values from SpellEffect 1329283 and 1329549:
50% weapon damage (effect 31), 5 Energy, a 10 s cooldown, and 15 (rank 1, level 24) or 25 (rank 2, level 44) Energy
back (effect 30, power type 3). On cooldown it nets (25 - 5) / 10 = 2 Energy a second at 60. Flash of Steel 5/5
adds 15 Energy and cuts 2 s: (25 + 15 - 5) / 8 = 4.375. Boot Knife 5/5 adds 2 Combo Points to every landed Shank.
Venom: +30% poison damage and +20% poison chance for 6 s of every Shank cooldown. Poised and Composure work only out
of combat (once a pull), so they stay out."""

import pytest

from wowforever.classes import class_module
from wowforever.classes.rogue_rotation import rogue_rotation
from wowforever.effects import attach_effects
from wowforever.melee_stats import MeleeStats
from wowforever.physical import Attacker, Target, land_chance, yellow_attack
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

R = class_module("rogue")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("rogue"), R.TALENT_EFFECTS, R.UNMODELED)
STATS = MeleeStats(level=60, strength=100, agility=200, stamina=100, intellect=30, attack_power=600,
                   ranged_attack_power=300, crit_pct=15, ranged_crit_pct=15, hit_pct=3, health=3000,
                   mana=0, main_hand=(100, 200, 2.6), off_hand=(60, 110, 1.8), ranged=None)
BOSS = Target(level_diff=3, armor=3731)
NO_SHANK = [s for s in CLS.spells if s.name != "Shank"]


def ranks(**talents):
    return {CLS.talent_named(n.replace("_", " ")).talent_id: r for n, r in talents.items()}


def test_shank_in_the_data():
    shank = {s.rank: s for s in CLS.spells if s.name == "Shank"}
    assert [(s.spell_id, s.level, s.energy_cost, s.energy_gain, s.cooldown, s.weapon_pct, s.weapon_hits)
            for s in shank.values()] == [(1329283, 24, 5, 15, 10.0, 50.0, 1), (1329549, 44, 5, 25, 10.0, 50.0, 1)]


def test_rules():
    assert PROBLEMS == []
    rules = {n: [(e.kind, e.applies_to, e.values[-1]) for e in CLS.talent_named(n).effects]
             for n in ("Flash of Steel", "Boot Knife", "Venom")}
    assert rules == {
        "Flash of Steel": [("resource", ("@shank_energy",), 15.0), ("cooldown", ("Shank",), -2.0)],
        "Boot Knife": [("proc_chance", ("@shank_combo",), 100.0)],
        "Venom": [("damage_pct", ("@venom",), 30.0), ("proc_chance", ("@venom",), 20.0)],
    }


def test_shank_energy_on_cooldown():
    assert rogue_rotation(STATS, NO_SHANK, CLS, {}, BOSS).energy_per_second == pytest.approx(10.0)
    assert rogue_rotation(STATS, CLS.spells, CLS, {}, BOSS).energy_per_second == pytest.approx(12.0)
    flash = rogue_rotation(STATS, CLS.spells, CLS, ranks(Flash_of_Steel=5), BOSS)
    assert flash.energy_per_second == pytest.approx(10.0 + (25 + 15 - 5) / 8)


def test_shank_damage_is_an_off_hand_strike():
    a = Attacker(60, 600, 15, 3)
    with_shank = rogue_rotation(STATS, CLS.spells, CLS, {}, BOSS)
    without = rogue_rotation(STATS, NO_SHANK, CLS, {}, BOSS)
    shank = yellow_attack(((60 + 110) / 2 + 600 / 14 * 1.8) * 0.5, a, BOSS)
    # more Energy means more Sinister Strike cycles too; the strike itself is a tenth of a Shank a second
    extra_cycles = with_shank.cycles_per_second - without.cycles_per_second
    assert extra_cycles > 0
    assert with_shank.yellow_dps - without.yellow_dps - (with_shank.poison_dps - without.poison_dps) == pytest.approx(
        0.1 * shank + extra_cycles / without.cycles_per_second * (without.yellow_dps - without.poison_dps))


def test_boot_knife_combo_points_shorten_the_cycle():
    land = land_chance(Attacker(60, 600, 15, 3), BOSS)
    r = rogue_rotation(STATS, CLS.spells, CLS, ranks(Boot_Knife=5), BOSS)
    ss, evis = best_rank(CLS.spells, "Sinister Strike", 60), best_rank(CLS.spells, "Eviscerate", 60)
    cp, k = land, 5                      # one combo point per landed Sinister Strike, no crit procs taken
    s = 0.1 * land * 2                   # Boot Knife: 2 points per landed Shank, a Shank every 10 s
    expected = (12.0 + s * ss.energy_cost / cp) / (k / cp * ss.energy_cost + evis.energy_cost)
    assert r.cycles_per_second == pytest.approx(expected)


def test_venom_raises_the_poisons():
    plain = rogue_rotation(STATS, CLS.spells, CLS, {}, BOSS)
    venom = rogue_rotation(STATS, CLS.spells, CLS, ranks(Venom=1), BOSS)
    assert venom.poison_dps > plain.poison_dps
    assert venom.dps - venom.poison_dps == pytest.approx(plain.dps - plain.poison_dps)    # only the poisons move


def test_no_off_hand_no_shank():
    one_hand = MeleeStats(**{**STATS.__dict__, "off_hand": None})
    assert rogue_rotation(one_hand, CLS.spells, CLS, {}, BOSS).energy_per_second == pytest.approx(10.0)
