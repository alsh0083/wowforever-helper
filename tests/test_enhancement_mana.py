"""Enhancement mana (#398): Earth Shock on its cooldown and Stormstrike cost mana (Fire Nova too on packs);
Improved Stormstrike keeps chance x 50% of Spirit regen going while casting ((15 + Spirit / 5) per 2 s tick,
Classic, config/melee.toml [shaman_melee]). Once dry the shaman swings white with Windfury, and a raid can also
drop Earth Shock (an alternative, as #390's DoT drops)."""

import pytest

from wowforever import melee_scenarios as ms
from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.shaman_rotation import enhancement_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import Target
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

S = class_module("shaman")
CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("shaman"), S.TALENT_EFFECTS,
                               S.UNMODELED)
STATS = MeleeStatTable.load("shaman_melee").at(60)
BOSS = Target(3, 3731)
BUILD = next(b for b in load_builds(class_name="shaman") if b.id == "shaman-enhancement").final_ids(CLS)


def total(ranks, kind, applies):
    return sum(e.values[ranks[t.talent_id] - 1] for t in CLS.talents if ranks.get(t.talent_id, 0) > 0
               for e in t.effects if e.kind == kind and applies in e.applies_to)


def spell(name):
    return best_rank(CLS.spells, name, 60)


def test_rule():
    assert PROBLEMS == []
    (rule,) = [e for e in CLS.talent_named("Improved Stormstrike").effects if e.kind == "regen_while_casting"]
    assert (rule.applies_to, rule.values) == (("@stormstrike",), (25.0, 50.0))


def test_mana_by_hand():
    assert total(BUILD, "regen_while_casting", "@stormstrike") > 0      # the build takes Improved Stormstrike
    shock, storm = spell("Earth Shock"), spell("Stormstrike")
    period = max(shock.cooldown + total(BUILD, "cooldown", "Earth Shock"), 1.5)
    shock_mana = shock.mana_cost * (1 + total(BUILD, "mana_cost_pct", "Earth Shock") / 100) / period
    regen = total(BUILD, "regen_while_casting", "@stormstrike") / 100 * (15 + STATS.spirit / 5) / 2
    r = enhancement_rotation(STATS, CLS.spells, CLS, BUILD, BOSS)
    assert r.shock_mana_per_second == pytest.approx(shock_mana)
    assert r.mana_per_second == pytest.approx(shock_mana + storm.mana_cost / storm.cooldown - regen)


def test_no_stormstrike_no_regen():
    shock = spell("Earth Shock")
    r = enhancement_rotation(STATS, CLS.spells, CLS, {}, BOSS)
    assert r.mana_per_second == pytest.approx(shock.mana_cost / shock.cooldown)


def test_fire_nova_mana_on_packs():
    nova = spell("Fire Nova")
    one = enhancement_rotation(STATS, CLS.spells, CLS, BUILD, BOSS).mana_per_second
    pack = enhancement_rotation(STATS, CLS.spells, CLS, BUILD, BOSS, pack=3).mana_per_second
    period = max(nova.cooldown + total(BUILD, "cooldown", "Fire Nova"), 1.5)
    assert pack - one == pytest.approx(nova.mana_cost * (1 + total(BUILD, "mana_cost_pct", "Fire Nova") / 100)
                                       / period)


def test_parts():
    r = enhancement_rotation(STATS, CLS.spells, CLS, BUILD, BOSS)
    assert 0 < r.windfury_dps < r.yellow_dps                           # Stormstrike is the rest
    assert 0 < r.shock_dps <= r.spell_dps


def test_output_falls_back_to_swings_and_can_drop_the_shock():
    r = enhancement_rotation(STATS, CLS.spells, CLS, BUILD, BOSS)
    out = S._melee_output(STATS, CLS.spells, CLS, BUILD, BOSS)
    fallback = r.white_dps + r.windfury_dps
    assert out == ms.Output(r.dps, r.mana_per_second, fallback, r.aoe, alternatives=(
        ms.Output(r.dps - r.shock_dps, r.mana_per_second - r.shock_mana_per_second, fallback, r.aoe),))
