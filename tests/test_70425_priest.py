"""1.60.1.70425 priest talents (#356), on the pinned dataset."""

import pytest

from wowforever.builds import load_builds
from wowforever.classes.priest import TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.schema import Dataset, latest_dataset_path

CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("priest"), TALENT_EFFECTS, UNMODELED)
STATS = stat_table("priest").at(60)


def effects(name):
    return {(e.kind, e.applies_to): e.values for e in CLS.talent_named(name).effects}


def test_every_priest_talent_maps():
    assert PROBLEMS == []
    assert not {"Shadow Affinity", "Improved Fade"} & set(UNMODELED)


def test_shadow_weaving_reads_the_target_debuff_text():
    assert effects("Shadow Weaving")[("damage_pct", ("shadow",))] == pytest.approx((3.3, 6.7, 10.0))


def test_improved_mind_flay_ramps_each_tick():
    # 3 ticks, each x% more than the one before: mean multiplier ((1+x)^3 - 1) / 3x
    assert effects("Improved Mind Flay")[("damage_pct", ("Mind Flay",))] == pytest.approx(
        ((1.331 - 1) / 0.3 * 100 - 100, (1.728 - 1) / 0.6 * 100 - 100))


def test_improved_mind_blast_is_half_a_second_a_rank():
    assert effects("Improved Mind Blast") == {("cooldown", ("Mind Blast",)): (-0.5, -1.0, -1.5, -2.0, -2.5)}


def test_mental_strength_and_dark_inspiration_raise_stats():
    assert effects("Mental Strength") == {("stat_pct", ("intellect",)): (2.0, 4.0, 6.0, 8.0, 10.0)}
    assert effects("Dark Inspiration") == {("stat_pct", ("spirit",)): (3.0, 6.0, 9.0, 12.0, 15.0)}


def test_talent_stats_apply_the_build_percentages():
    from wowforever.caster import talent_stats

    ranks = {b.id: b for b in load_builds(class_name="priest")}["priest-shadow"].final_ids(CLS)
    # priest-shadow (the players' post-patch build, #369) takes Mental Strength 5 (10%) and Dark Inspiration 3 (9%)
    out = talent_stats("priest", STATS, CLS, ranks)
    assert out.intellect == pytest.approx(STATS.intellect * 1.10)
    assert out.spirit == pytest.approx(STATS.spirit * 1.09)
    assert out.mana > STATS.mana and out.crit_pct > STATS.crit_pct
    assert talent_stats("priest", STATS, CLS, {}) == STATS
