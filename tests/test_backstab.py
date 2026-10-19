"""Backstab (#392): with a dagger in the main hand, Backstab is the builder. The stat rows carry no weapon type, so
the dagger is the main hand's weapon DPS at the dagger speed (config/rogue.toml `dagger_speed`), and the rogue
takes whichever of that and its usual weapon scores higher (owner: the best weapon for the scenario, #386).
Puncturing Wounds' extra combo point counts at its chance on every landed Backstab."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.classes.rogue_rotation import rogue_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Attacker, Target, land_chance
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.toml_cache import load_toml
from wowforever.weapon_talents import best_weapon

R = class_module("rogue")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("rogue"), R.TALENT_EFFECTS,
                               R.UNMODELED)
STATS = stat_table("rogue").at(60)
BOSS = Target(3, 3731)
DAGGER_SPEED = load_toml(Path(__file__).resolve().parents[1] / "config" / "rogue.toml")["dagger_speed"]


def ranks(**by_name):
    return {CLS.talent_named(n.replace("_", " ")).talent_id: r for n, r in by_name.items()}


def test_dagger_keeps_the_weapon_dps():
    d = R.dagger(STATS)
    mn, mx, speed = STATS.main_hand
    assert d.main_hand[2] == DAGGER_SPEED == 1.8
    assert (d.main_hand[0] + d.main_hand[1]) / 2 / d.main_hand[2] == pytest.approx((mn + mx) / 2 / speed)
    assert d.main_hand[0] == pytest.approx(mn * 1.8 / speed) and d.off_hand == STATS.off_hand


def test_backstab_is_the_builder_only_when_asked():
    assert rogue_rotation(STATS, CLS.spells, CLS, {}, BOSS).builder == "Sinister Strike"
    assert rogue_rotation(R.dagger(STATS), CLS.spells, CLS, {}, BOSS, backstab=True).builder == "Backstab"
    # Mutilate keeps its place
    mut = ranks(Mutilate=1)
    assert rogue_rotation(R.dagger(STATS), CLS.spells, CLS, mut, BOSS, backstab=True).builder == "Mutilate"


def test_puncturing_wounds_extra_combo_points():
    stats = R.dagger(STATS)
    r = rogue_rotation(stats, CLS.spells, CLS, ranks(Puncturing_Wounds=3), BOSS, backstab=True)
    land = land_chance(Attacker(60, stats.attack_power, stats.crit_pct, stats.hit_pct), BOSS)
    n = 5 / (land * (1 + 0.45))
    bs, evis = best_rank(CLS.spells, "Backstab", 60), best_rank(CLS.spells, "Eviscerate", 60)
    assert r.builder == "Backstab"
    assert r.cycles_per_second == pytest.approx(10.0 / (n * bs.energy_cost + evis.energy_cost))


def test_hack_and_slash_only_dagger():
    # stand-in rotation as in test_weapon_talents: dps = 100 + 2 x crit - armor / 100; heavy armor favours the mace
    @dataclass(frozen=True)
    class Stats:
        crit_pct: float

    @dataclass(frozen=True)
    class Result:
        dps: float
        white_dps: float

    def run(stats, target):
        return Result(100 + 2 * stats.crit_pct - target.armor / 100, 40.0)

    talents = ranks(Hack_and_Slash=3)
    assert best_weapon(run, Stats(10), Target(3, 10000), CLS, talents)[1] == "mace"
    r, weapon = best_weapon(run, Stats(10), Target(3, 10000), CLS, talents, only="dagger")
    assert weapon == "dagger" and r.dps == pytest.approx(100 + 26 - 100)


@pytest.mark.parametrize("talents", [{}, {"Puncturing_Wounds": 3, "Opportunity": 2}, {"Hack_and_Slash": 3}])
def test_output_takes_the_better_weapon(talents):
    rk = ranks(**talents)
    usual = best_weapon(lambda s, t: rogue_rotation(s, CLS.spells, CLS, rk, t), STATS, BOSS, CLS, rk)[0]
    stab = best_weapon(lambda s, t: rogue_rotation(s, CLS.spells, CLS, rk, t, backstab=True), R.dagger(STATS),
                       BOSS, CLS, rk, only="dagger")[0]
    assert R.output(STATS, CLS.spells, CLS, rk, BOSS).dps == pytest.approx(max(usual.dps, stab.dps))
