"""Destruction warlock rotation (#385): Shadowburn on cooldown, Shadow and Flame's Fire bonus, and Conflagrate
consuming Immolate unless Shadow and Flame keeps it (20% per rank)."""

import pytest

from wowforever.builds import load_builds
from wowforever.caster import caster_rotation, consumed_period
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warlock")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("warlock"), W.TALENT_EFFECTS,
                               W.UNMODELED)
BUILDS = {b.id: b.final_ids(CLS) for b in load_builds(class_name="warlock")}
STATS = stat_table("warlock").at(60)
BOSS = Target(3, 0)


def test_consumed_period_by_hand():
    # Immolate 15 s, Conflagrate every 10 s: consumed -> 10 s; always kept -> 15 s; 60% kept -> 9 + 4 = 13 s
    assert consumed_period(15.0, 10.0, 0.0) == 10.0
    assert consumed_period(15.0, 10.0, 100.0) == 15.0
    assert consumed_period(15.0, 10.0, 60.0) == pytest.approx(13.0)
    assert consumed_period(15.0, 20.0, 0.0) == 15.0       # a slower consumer never cuts it short


def test_rotation_plan():
    assert "Shadowburn" in W.ROTATION["cooldowns"] and W.ROTATION["consumes"] == {"Conflagrate": "Immolate"}


def test_shadow_and_flame_rules():
    assert PROBLEMS == []
    effects = {(e.kind, e.applies_to): e.values for e in CLS.talent_named("Shadow and Flame").effects}
    assert effects[("damage_pct", ("shadow",))][-1] == 10
    assert effects[("damage_pct", ("fire",))][-1] == 10
    assert effects[("proc_chance", ("@keep_Immolate",))] == (20, 40, 60, 80, 100)


def test_destruction_casts_shadowburn_and_conflagrate():
    r = caster_rotation("warlock", STATS, CLS.spells, CLS, BUILDS["warlock-destruction-pve"], BOSS)
    assert "Shadowburn" in r.spells and "Conflagrate" in r.spells and "Immolate" in r.spells


def test_conflagrate_without_shadow_and_flame_costs_immolate_damage(monkeypatch):
    ranks = BUILDS["warlock-demonology-pve-model"]
    assert ranks.get(CLS.talent_named("Shadow and Flame").talent_id, 0) == 0
    consumed = caster_rotation("warlock", STATS, CLS.spells, CLS, ranks, BOSS).dps
    monkeypatch.setitem(W.ROTATION, "consumes", {})
    assert caster_rotation("warlock", STATS, CLS.spells, CLS, ranks, BOSS).dps > consumed
