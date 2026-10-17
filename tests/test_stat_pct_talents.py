"""Percent-stat talents (#383): Ancestral Knowledge, Heart of the Wild, Living Spirit, Divine Intellect and
Divine Strength raise a stat by a share of the build's own, on the caster row (caster.talent_stats) or the melee
row (engines.melee_talent_stats). Hand values: stat x (1 + rank-5 percent), Strength worth 2 attack power."""

import pytest

from wowforever.caster import talent_stats
from wowforever.classes import class_module
from wowforever.classes.engines import melee_talent_stats
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.schema import Dataset, latest_dataset_path

DS = Dataset.load(latest_dataset_path())


def loaded(name):
    m = class_module(name)
    return attach_effects(DS.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)


def rank(cls, name, r):
    return {cls.talent_named(name).talent_id: r}


@pytest.mark.parametrize("name", ["shaman", "druid", "paladin"])
def test_rules_parse(name):
    cls, problems = loaded(name)
    assert problems == []


@pytest.mark.parametrize("cls_name,talent,stat,pct", [
    ("shaman", "Ancestral Knowledge", "intellect", 10), ("druid", "Heart of the Wild", "intellect", 10),
    ("druid", "Living Spirit", "spirit", 15)])
def test_caster_row(cls_name, talent, stat, pct):
    cls, _ = loaded(cls_name)
    row = stat_table(cls_name).at(60).caster
    after = talent_stats(cls_name, row, cls, rank(cls, talent, cls.talent_named(talent).max_rank))
    assert getattr(after, stat) == pytest.approx(getattr(row, stat) * (1 + pct / 100))


def test_divine_strength_on_the_paladin_melee_row():
    cls, _ = loaded("paladin")
    row = stat_table("paladin").at(60)
    after = melee_talent_stats("paladin", row, cls, rank(cls, "Divine Strength", 5))
    assert after.strength == pytest.approx(row.strength * 1.10)
    assert after.attack_power == pytest.approx(row.attack_power + 2 * row.strength * 0.10)


def test_heart_of_the_wild_on_the_feral_melee_row():
    cls, _ = loaded("druid")
    hybrid = stat_table("druid").at(60)
    after = melee_talent_stats("druid", hybrid, cls, rank(cls, "Heart of the Wild", 5))
    assert after.melee.strength == pytest.approx(hybrid.melee.strength * 1.10)
    assert after.melee.intellect == pytest.approx(hybrid.melee.intellect * 1.10)
    assert after.caster == hybrid.caster


def test_caster_row_skips_strength():
    # Heart of the Wild's Cat Form Strength does nothing for a caster row, which has no Strength
    cls, _ = loaded("druid")
    row = stat_table("druid").at(60).caster
    assert talent_stats("druid", row, cls, rank(cls, "Heart of the Wild", 5)).spirit == row.spirit


def test_divine_strength_raises_retribution_output():
    from wowforever.builds import load_builds
    from wowforever.classes import engine
    from wowforever.physical import Target

    cls, _ = loaded("paladin")
    ranks = {b.id: b.final_ids(cls) for b in load_builds(class_name="paladin")}["paladin-retribution"]
    ds = cls.talent_named("Divine Strength").talent_id
    assert ranks.get(ds, 0) > 0
    stats = stat_table("paladin").at(60)
    full = engine("paladin").output(stats, cls.spells, cls, ranks, Target(3, 0)).dps
    without = engine("paladin").output(stats, cls.spells, cls, {t: r for t, r in ranks.items() if t != ds},
                                       Target(3, 0)).dps
    assert full > without
