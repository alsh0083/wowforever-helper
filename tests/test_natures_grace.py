"""Nature's Grace (#397): a spell crit makes the next cast (and its global cooldown) 10% faster; on average every
cast is faster by crit chance x 10%."""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.caster import cast, caster_rotation
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

D = class_module("druid")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("druid"), D.TALENT_EFFECTS, D.UNMODELED)
STATS = stat_table("druid").at(60).caster
GRACE = {CLS.talent_named("Nature's Grace").talent_id: 1}


def test_rule_parses():
    assert PROBLEMS == []
    (rule,) = CLS.talent_named("Nature's Grace").effects
    assert (rule.kind, rule.values) == ("crit_haste_pct", (10.0,))


@pytest.mark.parametrize("spell", ["Starfire", "Wrath", "Moonfire"])
def test_casts_are_faster_by_crit_chance_times_ten_percent(spell):
    s = best_rank(CLS.spells, spell, 60)
    a = Assumptions.load()
    plain, graced = cast(s, STATS, CLS, {}, 63, a), cast(s, STATS, CLS, GRACE, 63, a)
    assert graced[1] == pytest.approx(plain[1] * (1 - 0.10 * STATS.crit_pct / 100))
    assert (graced[0], graced[2]) == (plain[0], plain[2])


def test_balance_rotation_gains():
    ranks = {b.id: b.final_ids(CLS) for b in load_builds(class_name="druid")}["druid-balance"]
    tid = CLS.talent_named("Nature's Grace").talent_id
    assert ranks.get(tid, 0) == 1
    without = {t: r for t, r in ranks.items() if t != tid}
    assert (caster_rotation("druid", STATS, CLS.spells, CLS, ranks, Target(3, 0)).dps
            > caster_rotation("druid", STATS, CLS.spells, CLS, without, Target(3, 0)).dps)
