"""Nightfall (#396): each Corruption tick has a 4% chance to make the next Shadow Bolt instant. A proc saves
Shadow Bolt's cast time minus the global cooldown, and that time goes to more Shadow Bolts:
extra Shadow Bolts per second = procs per second x saved seconds / Shadow Bolt's cast time."""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.caster import cast, caster_rotation
from wowforever.calc.ev import GCD_SECONDS
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warlock")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("warlock"), W.TALENT_EFFECTS,
                               W.UNMODELED)
STATS = stat_table("warlock").at(60)
NIGHTFALL = {CLS.talent_named("Nightfall").talent_id: 2}
BOSS = Target(3, 0)


def test_rule():
    assert PROBLEMS == []
    (rule,) = CLS.talent_named("Nightfall").effects
    assert rule.kind == "instant_proc_pct" and rule.values == (2.0, 4.0)
    assert set(rule.applies_to) == {"Corruption", "Drain Soul", "Drain Life", "Wrack", "@Shadow Bolt"}


def test_extra_shadow_bolts_by_hand():
    base = caster_rotation("warlock", STATS, CLS.spells, CLS, {}, BOSS)
    night = caster_rotation("warlock", STATS, CLS.spells, CLS, NIGHTFALL, BOSS)
    assert base.spells == night.spells and "Corruption" in night.spells and night.spells[-1] == "Shadow Bolt"
    corruption = best_rank(CLS.spells, "Corruption", 60)
    ev, seconds, cost = cast(best_rank(CLS.spells, "Shadow Bolt", 60), STATS, CLS, NIGHTFALL, 63, Assumptions.load())
    procs = 0.04 / corruption.tick_period                      # per second
    extra = procs * (seconds - GCD_SECONDS) / seconds          # Shadow Bolts per second
    assert night.dps - base.dps == pytest.approx(extra * ev)
    assert night.mana_per_second - base.mana_per_second == pytest.approx(extra * cost)


def test_no_gain_when_shadow_bolt_is_not_the_filler(monkeypatch):
    monkeypatch.setitem(W.ROTATION, "fillers", ("Searing Pain",))
    assert (caster_rotation("warlock", STATS, CLS.spells, CLS, NIGHTFALL, BOSS).dps
            == pytest.approx(caster_rotation("warlock", STATS, CLS.spells, CLS, {}, BOSS).dps))
