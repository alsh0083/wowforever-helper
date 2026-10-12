"""Druid healing talents in self-healing (#276).

Talents that name a heal change its cast time and mana cost; Gift of Nature (new effect kind
`healing_pct`) multiplies all healing. Moonglow cuts only *damaging* spells' cost, so heals skip
school-wide effects: only effects naming the heal by name, plus `healing_pct`, apply.

Rank texts (Forever): Naturalist -0.1 s Healing Touch cast per rank; Gift of Nature +2% healing per
rank; Tranquil Spirit -2% Healing Touch and Tranquility mana cost per rank.

Healing amounts with these talents are pinned in tests/test_hot_heals.py (#279).
"""

import pytest

from wowforever.classes.druid import TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.schema import Dataset, latest_dataset_path

CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("druid"), TALENT_EFFECTS, UNMODELED)


def effects(name):
    return {e.kind: (e.values, e.applies_to) for e in next(t for t in CLS.talents if t.name == name).effects}


def test_healing_talents_parse_from_their_rank_texts():
    assert PROBLEMS == []
    assert effects("Naturalist")["cast_time"] == (pytest.approx((-0.1, -0.2, -0.3, -0.4, -0.5)), ("Healing Touch",))
    assert effects("Gift of Nature")["healing_pct"] == ((2.0, 4.0, 6.0, 8.0, 10.0), ("all",))
    assert effects("Tranquil Spirit")["mana_cost_pct"] == ((-2.0, -4.0, -6.0, -8.0, -10.0),
                                                           ("Healing Touch", "Tranquility"))
