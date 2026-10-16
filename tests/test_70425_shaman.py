"""1.60.1.70425 shaman talents (#357), on the pinned dataset."""

import pytest

from wowforever.classes.shaman import TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.schema import Dataset, latest_dataset_path

CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("shaman"), TALENT_EFFECTS, UNMODELED)


def test_every_shaman_talent_maps():
    assert PROBLEMS == []
    assert "Call of Thunder" not in TALENT_EFFECTS and "Improved Fire Nova" not in UNMODELED
    assert "Trial by Fire" in UNMODELED


def test_elemental_mastery_is_its_uptime_share_of_half_a_second():
    # -0.5 s on Lightning Bolt and Lava Burst for 15 s every 180 s (wago SpellCooldowns, spell 16166)
    (effect,) = CLS.talent_named("Elemental Mastery").effects
    assert (effect.kind, effect.applies_to) == ("cast_time", ("Lightning Bolt", "Lava Burst"))
    assert effect.values == pytest.approx((-0.5 * 15 / 180,))
