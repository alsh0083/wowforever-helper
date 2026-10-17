"""Rogue poisons, part 2 (#387): poison damage per landed hit, and the best poison on each weapon.

Hand-worked: Instant Poison 76-100 (avg 88), Deadly Poison 92 over 12 s (5 stacks), proc chances 20% / 30%
(Classic; config/rogue.toml), a spell landing 83% of the time against a boss, 20% crit (x1.5) on Instant Poison,
Vile Poisons +20%."""

from dataclasses import replace

import pytest

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.poisons import best_poisons, poison_dps
from wowforever.classes.rogue_rotation import rogue_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Attacker, Target, white_land_chance
from wowforever.schema import Dataset, latest_dataset_path

R = class_module("rogue")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("rogue"), R.TALENT_EFFECTS, R.UNMODELED)
BASE = CLS.spells[0]
INSTANT = replace(BASE, name="Instant Poison", min_damage=76.0, max_damage=100.0, periodic_damage=0.0, duration=0.0)
DEADLY = replace(BASE, name="Deadly Poison", min_damage=0.0, max_damage=0.0, periodic_damage=92.0, duration=12.0,
                 tick_period=3.0)
CHANCE = {"Instant Poison": 20.0, "Deadly Poison": 30.0}
KW = dict(land=0.83, crit=0.2, damage_pct=20.0, max_stacks=5)


def test_instant_poison():
    # 2 hits/s x 20% x 0.83 x 88 x (1 + 0.2 x 0.5) x 1.2 = 38.565
    assert poison_dps(INSTANT, 2.0, chance_pct=20.0, **KW) == pytest.approx(38.565, abs=0.001)


def test_deadly_poison_caps_at_five_stacks():
    # 2 hits/s x 30% x 0.83 = 0.498 applications/s, x 12 s = 5.98 stacks -> 5; 5 x 92 / 12 x 1.2 = 46.0
    assert poison_dps(DEADLY, 2.0, chance_pct=30.0, **KW) == pytest.approx(46.0)
    # 0.5 hits/s: 0.1245 x 12 = 1.494 stacks; 1.494 x 92 / 12 x 1.2 = 13.745
    assert poison_dps(DEADLY, 0.5, chance_pct=30.0, **KW) == pytest.approx(13.745, abs=0.001)


def test_best_poisons_per_weapon():
    # main hand 1.5 hits/s, off hand 1.0. Instant per hit 0.2 x 0.83 x 88 x 1.1 x 1.2 = 19.2826.
    # I/I 48.21; I/D 28.92 + 27.49 = 56.41; D/I 41.23 + 19.28 = 60.52; D/D (2.5 hits, 5 stacks) 46.0
    dps, names = best_poisons((INSTANT, DEADLY), (1.5, 1.0), chance_pct=CHANCE, **KW)
    assert names == ("Deadly Poison", "Instant Poison") and dps == pytest.approx(60.51, abs=0.01)


def test_best_poisons_one_weapon_and_none_learned():
    dps, names = best_poisons((INSTANT,), (1.5,), chance_pct=CHANCE, **KW)
    assert names == ("Instant Poison",) and dps == pytest.approx(1.5 * 19.2826, abs=0.01)
    assert best_poisons((), (1.5, 1.0), chance_pct=CHANCE, **KW) == (0.0, ())


def test_white_land_chance():
    # boss row: 8% miss + 19% dual wield - (5 hit - 1 suppression) = 23% miss, 6.5% dodge -> 70.5% connect
    a = Attacker(60, 1000.0, 20.0, 5.0)
    assert white_land_chance(a, Target(3, 0), dual_wield=True) == pytest.approx(0.705)
    assert white_land_chance(a, Target(3, 0)) == pytest.approx(0.895)


def test_improved_poisons_parses():
    assert PROBLEMS == []
    rule = CLS.talent_named("Improved Poisons").effects[0]
    assert (rule.kind, rule.applies_to, rule.values[-1]) == ("proc_chance", ("@poison",), 10.0)


def test_rotation_adds_poisons_at_60_not_before_20():
    ranks = {b.id: b.final_ids(CLS) for b in load_builds(class_name="rogue")}["rogue-combat"]
    stats = stat_table("rogue").at(60)
    with_poisons = rogue_rotation(stats, CLS.spells, CLS, ranks, Target(3, 0))
    no_poisons = [s for s in CLS.spells if "Poison" not in s.name]
    without = rogue_rotation(stats, no_poisons, CLS, ranks, Target(3, 0))
    assert with_poisons.poisons and with_poisons.dps > without.dps and without.poisons == ()
    assert with_poisons.dps - without.dps == pytest.approx(with_poisons.poison_dps)
    assert rogue_rotation(stat_table("rogue").at(18), CLS.spells, CLS, ranks, Target(1, 0)).poisons == ()
