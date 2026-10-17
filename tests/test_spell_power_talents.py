"""Spell power talents (#396, #398): Demonic Knowledge (spell power = 100% of level), Mental Quickness (30% of
Intellect, on Enhancement's shocks) and Improved Drains (+20% drains)."""

import pytest

from wowforever.caster import talent_stats
from wowforever.calc.talents import modifiers_for
from wowforever.classes import class_module
from wowforever.classes.shaman_rotation import enhancement_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

DS = Dataset.load(latest_dataset_path())


def loaded(name):
    m = class_module(name)
    return attach_effects(DS.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)


def only(cls, name):
    t = cls.talent_named(name)
    return {t.talent_id: t.max_rank}


@pytest.mark.parametrize("name", ["warlock", "shaman"])
def test_rules_parse(name):
    assert loaded(name)[1] == []


def test_demonic_knowledge_adds_the_level_as_spell_power():
    cls, _ = loaded("warlock")
    row = stat_table("warlock").at(60)
    assert talent_stats("warlock", row, cls, only(cls, "Demonic Knowledge")).spell_power == pytest.approx(
        row.spell_power + 60)
    row40 = stat_table("warlock").at(40)
    assert talent_stats("warlock", row40, cls, only(cls, "Demonic Knowledge")).spell_power == pytest.approx(
        row40.spell_power + 40)


def test_improved_drains():
    cls, _ = loaded("warlock")
    for spell in ("Drain Life", "Wrack"):
        assert modifiers_for(best_rank(cls.spells, spell, 60), cls, only(cls, "Improved Drains")).damage_pct == 20
    assert modifiers_for(best_rank(cls.spells, "Shadow Bolt", 60), cls, only(cls, "Improved Drains")).damage_pct == 0


def test_mental_quickness_on_a_caster_row():
    cls, _ = loaded("shaman")
    row = stat_table("shaman").at(60).caster
    after = talent_stats("shaman", row, cls, only(cls, "Mental Quickness"))
    assert after.spell_power == pytest.approx(row.spell_power + 0.30 * row.intellect)


def test_mental_quickness_powers_enhancement_shocks():
    cls, _ = loaded("shaman")
    row = stat_table("shaman").at(60).melee
    shock = best_rank(cls.spells, "Earth Shock", 60)
    assert shock.coefficient > 0
    base = enhancement_rotation(row, cls.spells, cls, {}, Target(3, 0))
    quick = enhancement_rotation(row, cls.spells, cls, only(cls, "Mental Quickness"), Target(3, 0))
    # only the shock changes: its average damage gains coefficient x 30% of Intellect
    gain = shock.coefficient * 0.30 * row.intellect
    avg = (shock.min_damage + shock.max_damage) / 2
    assert quick.spell_dps == pytest.approx(base.spell_dps * (avg + gain) / avg)
    assert quick.white_dps == base.white_dps
