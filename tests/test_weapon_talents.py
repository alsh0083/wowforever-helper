"""Weapon-type talents (#386): each scenario takes the weapon branch with the most DPS. Golden values by hand
with a stand-in rotation: dps = 100 + 2 x crit - armor / 100, white_dps = 40."""

from dataclasses import dataclass

import pytest

from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.weapon_talents import best_weapon

DS = Dataset.load(latest_dataset_path())
WARRIOR, ROGUE = DS.class_data("warrior"), DS.class_data("rogue")


@dataclass(frozen=True)
class Stats:
    crit_pct: float


@dataclass(frozen=True)
class Result:
    dps: float
    white_dps: float


def run(stats, target):
    return Result(100 + 2 * stats.crit_pct - target.armor / 100, 40.0)


def flat(stats, target):
    return Result(200.0, 40.0)


def ranks(cls, name, rank):
    return {t.talent_id: rank for t in cls.talents if t.name == name}


def test_no_weapon_talent():
    r, weapon = best_weapon(run, Stats(10), Target(3, 3000), WARRIOR, {})
    assert weapon is None and r.dps == pytest.approx(90)


def test_weaponmaster_axe_wins_on_light_armor():
    # axe +5% crit: 100 + 30 - 30 = 100; mace ignores 15%: 100 + 20 - 25.5 = 94.5; sword 90 x 1.05 = 94.5
    r, weapon = best_weapon(run, Stats(10), Target(3, 3000), WARRIOR, ranks(WARRIOR, "Weaponmaster", 5))
    assert weapon == "axe" and r.dps == pytest.approx(100)


def test_weaponmaster_mace_wins_on_heavy_armor():
    # axe 100 + 30 - 100 = 30; mace 8500 armor: 100 + 20 - 85 = 35; sword 20 x 1.05 = 21
    r, weapon = best_weapon(run, Stats(10), Target(3, 10000), WARRIOR, ranks(WARRIOR, "Weaponmaster", 5))
    assert weapon == "mace" and r.dps == pytest.approx(35)


def test_sword_extra_attacks_count_as_white_damage():
    # crit and armor don't matter: sword 200 x 1.05 = 210, the extra 10 is white damage
    r, weapon = best_weapon(flat, Stats(10), Target(3, 3000), WARRIOR, ranks(WARRIOR, "Weaponmaster", 5))
    assert weapon == "sword" and r.dps == pytest.approx(210) and r.white_dps == pytest.approx(50)


def test_hack_and_slash_rank_3():
    # dagger +3% crit: 100 + 26 - 30 = 96; mace 9%: 100 + 20 - 27.3 = 92.7; sword 90 x 1.03 = 92.7
    r, weapon = best_weapon(run, Stats(10), Target(3, 3000), ROGUE, ranks(ROGUE, "Hack and Slash", 3))
    assert weapon == "dagger" and r.dps == pytest.approx(96)


def test_rank_text_matches_per_rank_values():
    # the data's rank 5 text: 5% crit, 15% of armor, 5% extra attack chance
    for cls, name in ((WARRIOR, "Weaponmaster"), (ROGUE, "Hack and Slash")):
        text = next(t for t in cls.talents if t.name == name).rank_text[4]
        assert "critical strike chance by 5%" in text and "15% of" in text and "5% chance" in text


def test_class_outputs_use_best_weapon():
    from wowforever.classes import rogue, warrior
    import inspect
    assert "best_weapon" in inspect.getsource(warrior.output)
    assert "best_weapon" in inspect.getsource(rogue.output)
