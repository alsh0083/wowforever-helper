"""Execute-phase talents (#392, #395, #396): a bonus below N% health counts at N% of its value, the share of a
steady fight the target spends below N% health. Quietus 10% below 35% -> 3.5%; Early Demise +30% crit at or
below 20% -> 6%; Decimation +6% below 35% -> 2.1%."""

import pytest

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.schema import Dataset, latest_dataset_path

DS = Dataset.load(latest_dataset_path())


def effects(cls_name, talent):
    m = class_module(cls_name)
    cls, problems = attach_effects(DS.class_data(cls_name), m.TALENT_EFFECTS, m.UNMODELED)
    assert problems == []
    return cls.talent_named(talent).effects


def test_quietus():
    (rule,) = effects("rogue", "Quietus")
    assert rule.kind == "damage_pct" and set(rule.applies_to) == {"Sinister Strike", "Ghostly Strike", "Hemorrhage"}
    assert rule.values[0] == pytest.approx(0.7) and rule.values[-1] == pytest.approx(3.5)


def test_early_demise():
    (rule,) = effects("priest", "Early Demise")
    assert rule.kind == "crit_chance" and rule.applies_to == ("Shadow Word: Death",)
    assert rule.values == pytest.approx((3.0, 6.0))


def test_decimation_damage_part():
    (rule,) = effects("warlock", "Decimation")
    assert rule.kind == "damage_pct" and set(rule.applies_to) == {"Shadow Bolt", "Searing Pain"}
    assert rule.values == pytest.approx((1.05, 2.1))


def test_below_health_helper():
    import re

    from wowforever.classes import below_health

    assert below_health(re.search(r"(\d+)% .* (\d+)%", "10% more damage below 35% health")) == pytest.approx(3.5)
