"""Weapon-damage abilities in the spell parser (#131, part 1). Spec: docs/tasks/131-weapon-abilities.md.
Rogue fixture, build 1.60.1.70205; top ranks."""

from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.normalize import read_tables
from wowforever.normalize_spells import class_spells

TABLES = read_tables(Path(__file__).parent / "fixtures" / "wago-1.60.1.70205-rogue")
SPELLS = class_spells(TABLES, skill_lines=class_module("rogue").SKILL_LINES)


def top(name):
    return max((s for s in SPELLS if s.name == name), key=lambda s: s.rank)


@pytest.mark.parametrize("name, bonus, pct, hits, normalized, combo", [
    ("Sinister Strike", 68, 0, 1, True, 1),     # normalized weapon damage + 68, 1 combo point
    ("Backstab", 150, 150, 1, True, 1),         # (weapon + 150) x 150%
    ("Ambush", 116, 250, 1, True, 1),           # (weapon + 116) x 250%
    ("Mutilate", 67, 75, 2, True, 2),           # rank 4 (level 60): two triggered hits, each +67, 2 combo points
])
def test_weapon_strikes(name, bonus, pct, hits, normalized, combo):
    s = top(name)
    assert (s.weapon_bonus, s.weapon_pct, s.weapon_hits, s.weapon_normalized, s.combo_points) == (
        bonus, pct, hits, normalized, combo)


def test_finisher_damage_per_combo_point():
    evis = top("Eviscerate")
    assert evis.per_combo_point == 170 and evis.weapon_hits == 0
    assert (evis.min_damage, evis.max_damage) == (54.0, 162.0)       # base 108, variance 1


def test_slice_and_dice_haste():
    assert top("Slice and Dice").haste_pct == 30


def test_spells_without_weapon_effects_keep_defaults():
    kick = top("Kick")
    assert (kick.weapon_bonus, kick.weapon_pct, kick.weapon_hits, kick.weapon_normalized,
            kick.per_combo_point, kick.combo_points, kick.haste_pct) == (0, 0, 0, False, 0, 0, 0)
