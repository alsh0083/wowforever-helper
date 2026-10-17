"""Improved Shadow Bolt (#396): a Shadow Bolt crit makes the target take 20% more Shadow damage for 12 s. Its
uptime is the chance that one of the Shadow Bolts cast in the last 12 s critted."""

import pytest

from wowforever.caster import caster_rotation, crit_debuff_uptime
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warlock")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("warlock"), W.TALENT_EFFECTS,
                               W.UNMODELED)
STATS = stat_table("warlock").at(60)
ISB = {CLS.talent_named("Improved Shadow Bolt").talent_id: 5}
BOSS = Target(3, 0)


def test_rules():
    assert PROBLEMS == []
    effects = {e.kind: (e.applies_to, e.values[-1]) for e in CLS.talent_named("Improved Shadow Bolt").effects}
    assert effects["crit_debuff_pct"] == (("Shadow Bolt", "shadow"), 20.0)
    assert effects["crit_debuff_seconds"] == (("Shadow Bolt", "shadow"), 12.0)


def test_uptime_by_hand():
    # 0.4 casts/s x 12 s = 4.8 casts; 10% crit: 1 - 0.9^4.8 = 0.3974
    assert crit_debuff_uptime(0.10, 0.4, 12.0) == pytest.approx(1 - 0.9 ** 4.8)
    assert crit_debuff_uptime(0.10, 0.0, 12.0) == 0.0


def test_raises_shadow_damage_when_shadow_bolt_is_the_filler():
    base = caster_rotation("warlock", STATS, CLS.spells, CLS, {}, BOSS)
    assert base.spells[-1] == "Shadow Bolt"
    isb = caster_rotation("warlock", STATS, CLS.spells, CLS, ISB, BOSS)
    assert base.dps < isb.dps < base.dps * 1.2
    assert isb.mana_per_second == pytest.approx(base.mana_per_second)


def test_no_gain_without_shadow_bolt_casts(monkeypatch):
    monkeypatch.setitem(W.ROTATION, "fillers", ("Searing Pain",))
    assert (caster_rotation("warlock", STATS, CLS.spells, CLS, ISB, BOSS).dps
            == pytest.approx(caster_rotation("warlock", STATS, CLS.spells, CLS, {}, BOSS).dps))
