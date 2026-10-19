"""Soul Siphon (#396): drains +12% per Affliction DoT up on the target (Corruption, Bane of Agony, Siphon Life; up
to 36%), through the rotation's `dot:` conditions. Elemental Devastation (#398): an Earth Shock crit gives +9%
melee crit for 10 s; its uptime is 1 - (1 - spell crit)^(Earth Shocks in 10 s)."""

import pytest

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


def test_soul_siphon_counts_the_dots_up():
    cls, problems = loaded("warlock")
    assert problems == []
    drain = best_rank(cls.spells, "Drain Life", 60)
    ranks = {cls.talent_named("Soul Siphon").talent_id: 3}
    assert modifiers_for(drain, cls, ranks).damage_pct == 0
    two = frozenset({"dot:Corruption", "dot:Bane of Agony", "dot:Immolate"})     # Immolate isn't Affliction
    assert modifiers_for(drain, cls, ranks, two).damage_pct == 24
    three = two | {"dot:Siphon Life"}
    assert modifiers_for(drain, cls, ranks, three).damage_pct == 36
    assert modifiers_for(best_rank(cls.spells, "Shadow Bolt", 60), cls, ranks, three).damage_pct == 0


def test_elemental_devastation_uptime_by_hand():
    cls, problems = loaded("shaman")
    assert problems == []
    row = stat_table("shaman").at(60).melee
    ranks = {cls.talent_named("Elemental Devastation").talent_id: 3}
    base = enhancement_rotation(row, cls.spells, cls, {}, Target(3, 0))
    dev = enhancement_rotation(row, cls.spells, cls, ranks, Target(3, 0))
    shock = best_rank(cls.spells, "Earth Shock", 60)
    spell_crit = min(1.0, row.crit_pct / 100)
    uptime = 1 - (1 - spell_crit) ** (10 / max(shock.cooldown, 1.5))
    assert dev.white_dps > base.white_dps
    # the melee row fights with 9% x uptime more crit; the shock itself is unchanged
    assert dev.spell_dps == pytest.approx(base.spell_dps)
    from dataclasses import replace

    bumped = enhancement_rotation(replace(row, crit_pct=row.crit_pct + 9 * uptime), cls.spells, cls, {},
                                  Target(3, 0))
    assert dev.white_dps == pytest.approx(bumped.white_dps)
