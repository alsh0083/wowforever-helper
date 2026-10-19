"""Simple damage and mana talents (#384, part 1): Twin Disciplines, Reverberation, Shamanistic Focus, Elemental
Focus and Fel Vitality as effect rules. Hand values are the rank texts' last-rank numbers; Elemental Focus is a
best-effort average (10% chance of a free next spell = 10% less mana)."""

import pytest

from wowforever.caster import talent_stats
from wowforever.calc.talents import modifiers_for
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

DS = Dataset.load(latest_dataset_path())


def loaded(name):
    m = class_module(name)
    return attach_effects(DS.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)


def only(cls, name):
    t = cls.talent_named(name)
    return {t.talent_id: t.max_rank}


def mods(cls, talent, spell):
    return modifiers_for(best_rank(cls.spells, spell, 60), cls, only(cls, talent))


@pytest.mark.parametrize("name", ["priest", "shaman", "warlock"])
def test_rules_parse(name):
    assert loaded(name)[1] == []


def test_twin_disciplines_on_instant_spells_only():
    cls, _ = loaded("priest")
    for spell in ("Shadow Word: Pain", "Devouring Plague", "Shadow Word: Death", "Holy Nova"):
        assert mods(cls, "Twin Disciplines", spell).damage_pct == 5
    assert mods(cls, "Twin Disciplines", "Mind Blast").damage_pct == 0
    assert mods(cls, "Twin Disciplines", "Smite").damage_pct == 0


def test_shamanistic_focus_and_elemental_focus():
    cls, _ = loaded("shaman")
    assert mods(cls, "Shamanistic Focus", "Flame Shock").mana_cost_pct == -45
    assert mods(cls, "Shamanistic Focus", "Earth Shock").mana_cost_pct == -45
    assert mods(cls, "Shamanistic Focus", "Lightning Bolt").mana_cost_pct == 0
    assert mods(cls, "Elemental Focus", "Lightning Bolt").mana_cost_pct == -10
    assert mods(cls, "Elemental Focus", "Flame Shock").mana_cost_pct == -10


def test_reverberation_cuts_shock_cooldowns():
    cls, _ = loaded("shaman")
    (rule,) = cls.talent_named("Reverberation").effects
    assert rule.kind == "cooldown" and rule.values[-1] == -1.0
    assert set(rule.applies_to) == {"Earth Shock", "Flame Shock", "Frost Shock"}


def test_fel_vitality_raises_max_mana():
    cls, _ = loaded("warlock")
    row = stat_table("warlock").at(60)
    after = talent_stats("warlock", row, cls, only(cls, "Fel Vitality"))
    assert after.mana == pytest.approx(row.mana * 1.15)
    assert after.intellect == row.intellect
