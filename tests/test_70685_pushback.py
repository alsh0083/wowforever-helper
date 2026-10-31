"""Pushback rules read the 1.60.1.70685 wording too (#444).

70685 rewords every pushback talent to "Gives your <spells> a N% chance to not lose casting time when you take
damage." (70425: "Gives you a N% chance to avoid/resist interruption caused by damage ...", and Eye of the Storm
"Reduces the pushback suffered ... by N%"). Same values, same spells; tests/test_side_immunity_pushback.py keeps
checking the pinned build's text.
"""

from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.schema import Dataset

ROOT = Path(__file__).resolve().parents[1]
DS_70685 = Dataset.load(ROOT / "data" / "datasets" / "1.60.1.70685.json")


@pytest.mark.parametrize(("name", "talent", "values", "applies_to"), [
    # Nature's Focus 70685 rank 5: "Gives your Arcane and Nature spells a 70% chance to not lose casting time ..."
    ("druid", "Nature's Focus", (14.0, 28.0, 42.0, 56.0, 70.0), ("arcane", "nature")),
    # Twilight Focus 70685 rank 3: "Gives your spells a 70% chance to not lose casting time ..."
    ("priest", "Twilight Focus", (23.0, 47.0, 70.0), ("all",)),
    # Eye of the Storm 70685 rank 3: "Gives your Lightning Bolt, Chain Lightning, and Lava Burst spells a 70% chance ..."
    ("shaman", "Eye of the Storm", (23.0, 47.0, 70.0), ("Lightning Bolt", "Chain Lightning", "Lava Burst")),
    # Intensity 70685 rank 3: "Gives your Destruction spells a 70% chance to not lose casting time ..."
    ("warlock", "Intensity", (23.0, 47.0, 70.0), ("destruction",)),
])
def test_pushback_rules_parse_the_70685_text(name, talent, values, applies_to):
    m = class_module(name)
    cls, problems = attach_effects(DS_70685.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)
    assert not [p for p in problems if talent in p]
    effects = [e for e in cls.talent_named(talent).effects if e.kind == "pushback_pct"]
    assert len(effects) == 1
    assert tuple(effects[0].values) == values
    assert tuple(effects[0].applies_to) == applies_to
