"""Maelstrom Weapon (#398): landed melee swings (Windfury's included) build stacks; at the cap the shaman casts a
Lightning Bolt with its cast time and mana cut by the per-stack % x stacks (100% at 5/5: instant and free).

The rank text gives no proc chance: config/shaman.toml's `maelstrom_weapon.ppm` is a best-effort guess (procs per
minute, normalized to the weapon's speed). A bolt with cast time left stops the swings for that long, so it is
cast only when it out-damages the swings it costs."""

from pathlib import Path

import pytest

from wowforever.calc.ev import miss_chance
from wowforever.classes import class_module
from wowforever.classes.shaman_rotation import enhancement_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import Attacker, Target, white_land_chance
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.toml_cache import load_toml

S = class_module("shaman")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("shaman"), S.TALENT_EFFECTS,
                               S.UNMODELED)
STATS = MeleeStatTable.load("shaman_melee").at(60)
BOSS = Target(3, 3731)
MW = CLS.talent_named("Maelstrom Weapon").talent_id
C = load_toml(Path(__file__).resolve().parents[1] / "config" / "shaman.toml")


def bolt_per_cap():
    """(Lightning Bolts per second, expected damage of one) with no other talents."""
    land = white_land_chance(Attacker(60, STATS.attack_power, STATS.crit_pct, STATS.hit_pct), BOSS)
    procs = C["maelstrom_weapon"]["ppm"] / 60 * (1 + C["windfury_chance"]) * land   # haste 1, so swings x speed = 1
    bolt = best_rank(CLS.spells, "Lightning Bolt", 60)
    hit = 1 - miss_chance(60, 63, STATS.hit_pct) / 100
    ev = hit * (bolt.min_damage + bolt.max_damage) / 2 * (1 + STATS.crit_pct / 100 * 0.5)
    return procs / C["maelstrom_weapon"]["stacks"], ev, bolt


def test_rule():
    assert PROBLEMS == []
    (rule,) = CLS.talent_named("Maelstrom Weapon").effects
    assert (rule.kind, rule.applies_to, rule.values) == ("stack_pct", ("@maelstrom",), (4.0, 8.0, 12.0, 16.0, 20.0))
    assert C["maelstrom_weapon"]["stacks"] == 5


def test_five_of_five_is_a_free_instant_bolt():
    rate, ev, _ = bolt_per_cap()
    base = enhancement_rotation(STATS, CLS.spells, CLS, {}, BOSS)
    r = enhancement_rotation(STATS, CLS.spells, CLS, {MW: 5}, BOSS)
    assert r.maelstrom_dps == pytest.approx(rate * ev)
    assert r.dps - base.dps == pytest.approx(rate * ev)
    assert r.mana_per_second == pytest.approx(base.mana_per_second)
    assert r.maelstrom_dps <= r.spell_dps


def test_three_points_pay_the_cast_time_left():
    rate, ev, bolt = bolt_per_cap()
    base = enhancement_rotation(STATS, CLS.spells, CLS, {}, BOSS)
    r = enhancement_rotation(STATS, CLS.spells, CLS, {MW: 3}, BOSS)
    left = 1 - 12.0 * 5 / 100                       # 12% per stack x 5 stacks
    gain = ev - (base.white_dps + base.windfury_dps) * bolt.cast_time * left
    if gain > 0:
        assert r.maelstrom_dps == pytest.approx(rate * gain)
        assert r.mana_per_second - base.mana_per_second == pytest.approx(rate * bolt.mana_cost * left)
    else:
        assert r.maelstrom_dps == 0.0 and r.mana_per_second == pytest.approx(base.mana_per_second)
