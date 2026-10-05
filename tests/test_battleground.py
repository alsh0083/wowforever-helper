"""Battleground score (#27): the formula, on real fixture data at 60."""

from pathlib import Path

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.calc.pvp_axes import control, survival
from wowforever.classes.mage import LAYOUT, SKILL_LINES, TALENT_EFFECTS, UNMODELED
from wowforever.classes.mage_rotation import rotation
from wowforever.consensus import Consensus
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells, ranks_of
from wowforever.pvp.battleground import ENDURANCE_SECONDS, KILL_REFERENCE, battleground
from wowforever.scenarios import Character
from wowforever.sources.wowforevertalent import parse_page
from wowforever.stats import StatTable

FIX = Path(__file__).parent / "fixtures"
CLS, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205"), LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
CLS, _ = attach_effects(CLS, TALENT_EFFECTS, UNMODELED)
SPELLS = class_spells(read_tables(FIX / "wago-1.60.1.70205-spells"), skill_lines=SKILL_LINES)
BUILDS = {b.id: b for b in load_builds(class_name="mage")}
A = Assumptions.load()


def char(build_id):
    return Character(60, StatTable.load("mage").at(60), SPELLS, CLS, BUILDS[build_id].final_ids(CLS))


def test_formula_matches_the_axes_and_consensus_weights():
    c, fb = char("deep-frost"), ranks_of(SPELLS, "Frostbolt")[-1]
    r = rotation(c, fb, target_level=60, assumptions=A, sustained=False)
    w = Consensus.load().scenarios["battleground"].mid()
    kill = min(1, r.dps / KILL_REFERENCE)
    endurance = min(1, c.stats.mana / r.mana_per_second / ENDURANCE_SECONDS)
    expected = (w["kill"] * kill + w["endurance"] * endurance
                + w["survival"] * survival(c, fb).score + w["control"] * control(c, fb).score)
    assert battleground(c, fb, A)["score"] == pytest.approx(expected)


def test_control_builds_beat_glass_cannons_in_battlegrounds():
    frost = battleground(char("deep-frost"), ranks_of(SPELLS, "Frostbolt")[-1], A)["score"]
    fire = battleground(char("deep-fire"), ranks_of(SPELLS, "Fireball")[-1], A)["score"]
    assert frost > fire
