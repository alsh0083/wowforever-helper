"""Bonuses while a DoT is up (#384, #395) and two cost talents (#392, #395): Lava Burst +20% with Flame Shock
(its own effect 1), Power in Light (Smite +10% on Shadow Word: Pain targets), Devouring Contagion (Devouring
Plague -50% mana) and Flawless Execution (Eviscerate -10 Energy)."""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.caster import cast, caster_rotation
from wowforever.calc.talents import modifiers_for
from wowforever.classes import class_module
from wowforever.classes.rogue_rotation import rogue_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

DS = Dataset.load(latest_dataset_path())
BOSS = Target(3, 0)


def loaded(name):
    m = class_module(name)
    return attach_effects(DS.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)


def only(cls, name):
    t = cls.talent_named(name)
    return {t.talent_id: t.max_rank}


@pytest.mark.parametrize("name", ["priest", "shaman", "rogue"])
def test_rules_parse(name):
    assert loaded(name)[1] == []


def test_power_in_light_needs_shadow_word_pain_up():
    cls, _ = loaded("priest")
    smite = best_rank(cls.spells, "Smite", 60)
    ranks = only(cls, "Power in Light")
    assert modifiers_for(smite, cls, ranks).damage_pct == 0
    assert modifiers_for(smite, cls, ranks, frozenset({"dot:Shadow Word: Pain"})).damage_pct == 10


def test_cast_takes_conditions_and_extra_damage():
    cls, _ = loaded("shaman")
    stats = stat_table("shaman").at(60).caster
    bolt = best_rank(cls.spells, "Lightning Bolt", 60)
    a = Assumptions.load()
    plain = cast(bolt, stats, cls, {}, 63, a)
    boosted = cast(bolt, stats, cls, {}, 63, a, extra_damage_pct=20.0)
    assert boosted[0] == pytest.approx(plain[0] * 1.2) and boosted[1:] == plain[1:]


def test_lava_burst_gets_its_flame_shock_bonus(monkeypatch):
    S = class_module("shaman")
    assert S.ROTATION["dot_bonus"] == {"Lava Burst": ("Flame Shock", 20.0)}
    cls, _ = loaded("shaman")
    ranks = {b.id: b.final_ids(cls) for b in load_builds(class_name="shaman")}["shaman-elemental"]
    stats = stat_table("shaman").at(60).caster
    with_bonus = caster_rotation("shaman", stats, cls.spells, cls, ranks, BOSS)
    assert "Flame Shock" in with_bonus.spells and "Lava Burst" in with_bonus.spells
    monkeypatch.setitem(S.ROTATION, "dot_bonus", {})
    assert caster_rotation("shaman", stats, cls.spells, cls, ranks, BOSS).dps < with_bonus.dps


def test_devouring_contagion_halves_devouring_plague_mana():
    cls, _ = loaded("priest")
    plague = best_rank(cls.spells, "Devouring Plague", 60)
    assert modifiers_for(plague, cls, only(cls, "Devouring Contagion")).mana_cost_pct == -50


def test_flawless_execution_speeds_the_energy_cycle():
    cls, _ = loaded("rogue")
    stats = stat_table("rogue").at(60)
    base = rogue_rotation(stats, cls.spells, cls, {}, BOSS)
    cheap = rogue_rotation(stats, cls.spells, cls, only(cls, "Flawless Execution"), BOSS)
    # cycles = energy / (builders x cost + Eviscerate cost); 10 less Energy per Eviscerate
    assert 1 / cheap.cycles_per_second == pytest.approx(1 / base.cycles_per_second - 10 / base.energy_per_second)
