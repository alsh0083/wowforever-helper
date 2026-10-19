"""Retribution: Consecration on one target and Divine Precision (#399); questing takes the best alternative.

Consecration is kept down on one target too (its base ticks per max(duration, cooldown), Champion of the Light's
spell power on its coefficient), for its mana; the Output offers the same rotation without it, and dungeon, raid
and now questing take whichever scores higher (questing: kills per hour, #390's alternatives). Divine Precision
raises Holy spell hit for Hammer of Wrath."""

import pytest

from wowforever import melee_scenarios as ms
from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.engines import melee_talent_stats
from wowforever.classes.paladin_rotation import paladin_rotation
from wowforever.effects import attach_effects
from wowforever.physical import Target
from wowforever.scenarios import _anchor_at, best_rank, default_params
from wowforever.schema import Dataset, latest_dataset_path

P = class_module("paladin")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("paladin"), P.TALENT_EFFECTS,
                               P.UNMODELED)
STATS = ms.stat_table("paladin").at(60)
BOSS = Target(3, 3731)
SOC = {CLS.talent_named("Seal of Command").talent_id: 1}
RET = next(b for b in load_builds(class_name="paladin") if b.id == "paladin-retribution").final_ids(CLS)


def test_rule():
    assert PROBLEMS == []
    (rule,) = CLS.talent_named("Divine Precision").effects
    assert (rule.kind, rule.applies_to, rule.values) == ("hit_chance", ("@holy_spell",), (6.0, 12.0, 18.0))


def test_consecration_on_one_target():
    cons = best_rank(CLS.spells, "Consecration", 60)
    period = max(cons.duration, cons.cooldown)
    r = paladin_rotation(STATS, CLS.spells, CLS, SOC, BOSS)
    assert "Consecration" in r.abilities and r.aoe == ()
    assert r.consecration_dps == pytest.approx(cons.periodic_damage / period)          # no spell power, no bonus
    assert r.consecration_mana_per_second == pytest.approx(cons.mana_cost / period)


def test_output_offers_the_rotation_without_consecration():
    stats = melee_talent_stats("paladin", STATS, CLS, RET)
    r = paladin_rotation(stats, CLS.spells, CLS, RET, BOSS)
    out = P.output(STATS, CLS.spells, CLS, RET, BOSS)
    assert out == ms.Output(r.dps, r.mana_per_second, r.white_dps, r.aoe, alternatives=(
        ms.Output(r.dps - r.consecration_dps, r.mana_per_second - r.consecration_mana_per_second, r.white_dps,
                  r.aoe),))


def test_divine_precision_raises_the_holy_damage():
    dp = {CLS.talent_named("Divine Precision").talent_id: 3}
    base = paladin_rotation(STATS, CLS.spells, CLS, SOC, BOSS)
    with_dp = paladin_rotation(STATS, CLS.spells, CLS, {**SOC, **dp}, BOSS)
    assert with_dp.holy_dps > base.holy_dps and with_dp.white_dps == pytest.approx(base.white_dps)


def test_questing_takes_the_best_alternative():
    level = 60
    q = default_params("questing", level)
    armor, mob_dps, eat = _anchor_at(ms._config()["questing"]["anchors"], level)
    out = P.output(STATS, CLS.spells, CLS, RET, Target(0, armor), drink_mana_per_second=q.drink_mana_per_second)
    assert out.alternatives
    best = max(ms.questing_kills_per_hour(o, q, mob_dps, eat) for o in (out, *out.alternatives))
    assert ms.questing("paladin", STATS, CLS.spells, CLS, RET) == pytest.approx(best)


def test_questing_kills_per_hour_by_hand():
    # 1500 HP mob at 100 DPS: 15 s; eat back 10 DPS x 15 s at 50/s = 3 s; drink 20 mana/s x 15 s at 100/s = 3 s;
    # travel 12 s: 3600 / (15 + 3 + 12) = 120
    class Q:
        mob_hp, drink_mana_per_second, travel_seconds = 1500.0, 100.0, 12.0

    assert ms.questing_kills_per_hour(ms.Output(100.0, 20.0, 100.0), Q, 10.0, 50.0) == pytest.approx(120.0)
    # a pet tanks: no eating, but still drinking
    assert ms.questing_kills_per_hour(ms.Output(100.0, 20.0, 100.0, pet=True), Q, 10.0, 50.0) == pytest.approx(120.0)
    assert ms.questing_kills_per_hour(ms.Output(100.0, 0.0, 100.0, pet=True), Q, 10.0, 50.0) == pytest.approx(
        3600 / 27)
