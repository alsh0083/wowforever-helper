"""Self-healing in the duel model (#265).

The duel side may heal: `heal_budget` (mana-limited healing for the fight) at `heal_hps` while
casting heals. Healing adds effective health but pauses damage: with H healing at r per second,
t_side += H / r and t_opponent = (health - opening + H) / net. The side heals only if that raises
its score.

Synthetic duel (no controls, full uptime): side 3000 health / 100 DPS, opponent 3000 / 200 melee.
  No healing: t_side = 3000/100 = 30, t_opp = 3000/200 = 15, score 15/45 = 0.3333.
  2000 healing at 400/s: t_side = 30 + 5 = 35, t_opp = 5000/200 = 25, score 25/60 = 0.41667.

The druid's healing values are pinned in tests/test_hot_heals.py (#279).
"""

import pytest

from wowforever.builds import load_builds
from wowforever.melee_scenarios import stat_table
from wowforever.pvp.class_pvp import class_side, heal_capacity
from wowforever.pvp.duel import Kit, Side, duel
from wowforever.schema import Dataset, latest_dataset_path

CLS = Dataset.load(latest_dataset_path()).class_data("druid")
TABLE = stat_table("druid")
KIT = Kit(id="test-melee", role="melee", stealth=False, dispels_buffs=False, health=3000, dps=200,
          opener_damage=0, opener_stun=0, controls=(), removes=(), immunity=None)


def side(**kw):
    base = dict(health=3000, dps=100, absorb_per_min=0, immunity_share=0, root=0, stun=0, slow=0, interrupt=0)
    return Side(**{**base, **kw})


def test_no_healing_is_the_plain_race():
    assert duel(side(), KIT, "mage_sees").score == pytest.approx(1 / 3)


def test_healing_extends_both_times_and_raises_the_score():
    r = duel(side(heal_hps=400, heal_budget=2000), KIT, "mage_sees")
    assert (r.t_side, r.t_opponent) == (pytest.approx(35), pytest.approx(25))
    assert r.score == pytest.approx(25 / 60)


def test_the_side_skips_healing_that_lowers_its_score():
    # vs a 50 DPS opponent: plain 30 s vs 60 s, score 0.6667. Healing 2000 at 60/s would take 33.3 s:
    # 63.3 s vs (3000 + 2000) / 50 = 100 s, score 0.612, lower, so the side doesn't heal
    # (healing pays only when heal rate / incoming DPS beats t_opponent / t_side: 60/50 = 1.2 < 2)
    weak = Kit(**{**KIT.__dict__, "dps": 50})
    plain = duel(side(), weak, "mage_sees")
    healed = duel(side(heal_hps=60, heal_budget=2000), weak, "mage_sees")
    assert plain.score == pytest.approx(2 / 3) and healed.score == pytest.approx(plain.score)
    assert healed.t_side == pytest.approx(30)


def ranks(build_id):
    build = next(b for b in load_builds(class_name="druid") if b.id == build_id)
    return build.final_ids(CLS)


def test_the_druid_side_carries_its_healing_and_other_classes_none():
    s = class_side("druid", TABLE.at(60), CLS.spells, CLS, ranks("druid-balance-pvp"))
    expected = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, ranks("druid-balance-pvp"))
    assert s.heal_hps > 0 and (s.heal_hps, s.heal_budget) == pytest.approx(expected)
    rogue = Dataset.load(latest_dataset_path()).class_data("rogue")
    r = class_side("rogue", stat_table("rogue").at(60), rogue.spells, rogue, {})
    assert (r.heal_hps, r.heal_budget) == (0.0, 0.0)
