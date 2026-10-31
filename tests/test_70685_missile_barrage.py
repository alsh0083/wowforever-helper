"""Missile Barrage on 1.60.1.70685 (#439): the tooltip drops the Arcane Missiles hit procs and adds Frost Blast.

70685 rank 2: "Gives your Arcane Blast spell a 40% chance, and your Arcane Wrath, Fireball, Frostbolt, Frost Blast,
and Frostfire Bolt spells a 20% chance to reduce the channeled duration of your next Arcane Missiles spell by 50%
..." (rank 1: 20% and 10%). forever-bugs #405 (NAB, 2026-10-19) said the AM-hit procs were removed in-game; the
data now agrees, so an Arcane Missiles filler gains nothing from the talent. tests/test_missile_barrage.py keeps
checking the 70425 text, which still has "your Arcane Missile hits a 10% chance".
"""

from pathlib import Path

import pytest

from wowforever.assumptions import Assumptions
from wowforever.classes import class_module
from wowforever.classes.mage_rotation import missile_barrage_rule, rotation
from wowforever.effects import attach_effects
from wowforever.scenarios import Character, best_rank
from wowforever.schema import Dataset
from wowforever.stats import Stats

ROOT = Path(__file__).resolve().parents[1]
M = class_module("mage")
CLS, _ = attach_effects(Dataset.load(ROOT / "data" / "datasets" / "1.60.1.70685.json").class_data("mage"),
                        M.TALENT_EFFECTS, M.UNMODELED)
STATS = Stats(60, intellect=270, spirit=190, stamina=220, spell_power=150, crit_pct=6, hit_pct=3,
              mana=3600, health=2900)
A = Assumptions.load().with_values(level_resistance=False)
MB = CLS.talent_named("Missile Barrage").talent_id


def test_rule_reads_the_70685_text():
    assert missile_barrage_rule(CLS, 2) == {"Arcane Blast": 40.0, "Arcane Missiles": 0.0, "Arcane Wrath": 20.0,
                                            "Fireball": 20.0, "Frostbolt": 20.0, "Frost Blast": 20.0,
                                            "Frostfire Bolt": 20.0}
    assert missile_barrage_rule(CLS, 1) == {"Arcane Blast": 20.0, "Arcane Missiles": 0.0, "Arcane Wrath": 10.0,
                                            "Fireball": 10.0, "Frostbolt": 10.0, "Frost Blast": 10.0,
                                            "Frostfire Bolt": 10.0}


def test_an_arcane_missiles_filler_gains_nothing():
    am = best_rank(CLS.spells, "Arcane Missiles", 60)

    def run(rank):
        return rotation(Character(60, STATS, CLS.spells, CLS, {MB: rank} if rank else {}), am,
                        target_level=63, assumptions=A, sustained=True)

    assert run(2).dps == pytest.approx(run(0).dps)
