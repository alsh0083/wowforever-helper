"""Eclipse (#397): each Wrath makes the next 2 Starfires 0.5 s faster. The rotation also weighs a mixed filler,
one Wrath then two Starfires with the cut (`ROTATION["filler_mix"]`), against each filler alone."""

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
ECLIPSE = {CLS.talent_named("Eclipse").talent_id: 3}
BOSS = Target(3, 0)


def test_rule_and_plan():
    assert PROBLEMS == []
    (rule,) = CLS.talent_named("Eclipse").effects
    assert (rule.kind, rule.applies_to, rule.values[-1]) == ("cast_time", ("Starfire", "@eclipse"), -0.5)
    assert D.ROTATION["filler_mix"] == ("Wrath", "Starfire", 2, "eclipse")


def test_starfire_is_faster_after_wrath():
    starfire = best_rank(CLS.spells, "Starfire", 60)
    a = Assumptions.load()
    plain = cast(starfire, STATS, CLS, ECLIPSE, 63, a)
    eclipsed = cast(starfire, STATS, CLS, ECLIPSE, 63, a, frozenset({"eclipse"}))
    assert eclipsed[1] == pytest.approx(plain[1] - 0.5) and eclipsed[0] == plain[0]


def test_the_mix_is_one_wrath_and_two_fast_starfires():
    a = Assumptions.load()
    w = cast(best_rank(CLS.spells, "Wrath", 60), STATS, CLS, ECLIPSE, 63, a)
    s = cast(best_rank(CLS.spells, "Starfire", 60), STATS, CLS, ECLIPSE, 63, a, frozenset({"eclipse"}))
    mix_dps = (w[0] + 2 * s[0]) / (w[1] + 2 * s[1])
    r = caster_rotation("druid", STATS, CLS.spells, CLS, ECLIPSE, BOSS)
    singles = [cast(best_rank(CLS.spells, n, 60), STATS, CLS, ECLIPSE, 63, a) for n in ("Wrath", "Starfire")]
    best_single = max(ev / seconds for ev, seconds, _ in singles)
    assert (r.spells[-1] == "Wrath + Starfire") == (mix_dps > best_single)


def test_balance_does_not_lose_from_eclipse():
    ranks = {b.id: b.final_ids(CLS) for b in load_builds(class_name="druid")}["druid-balance"]
    tid = CLS.talent_named("Eclipse").talent_id
    without = {t: r for t, r in ranks.items() if t != tid}
    assert (caster_rotation("druid", STATS, CLS.spells, CLS, ranks, BOSS).dps
            >= caster_rotation("druid", STATS, CLS.spells, CLS, without, BOSS).dps)
