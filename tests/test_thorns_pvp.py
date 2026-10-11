"""Thorns in the duel model (#265): a druid returns damage to melee attackers.

Hand-worked: Thorns rank 6 (level 54) is 18 per melee hit taken, rank 3 (level 24) 9 (client aura 15
base points, #261). The druid stat table gives the caster row 312 spell power at 60 and 93 at 30;
the melee (feral) row has none. With the 0.168 coefficient toggled on:
  60 Balance: 18 + 0.168 x 312 = 70.416 per hit;  30 Balance: 9 + 0.168 x 93 = 24.624 per hit.
The opponent's melee hits per second is a config estimate (1.0).
"""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.melee_scenarios import stat_table
from wowforever.pvp.class_pvp import class_side, thorns_dps
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

CLS = Dataset.load(latest_dataset_path()).class_data("druid")
TABLE = stat_table("druid")
ON = Assumptions.load().with_values(thorns_spell_power_coefficient=0.168)


def ranks(build_id):
    build = next(b for b in load_builds(class_name="druid") if b.id == build_id)
    return {CLS.talent_named(name).talent_id: r for name, r in build.final.items()}


def test_thorns_dps_is_damage_per_hit_times_hits():
    rank6 = best_rank(CLS.spells, "Thorns", 60)
    assert rank6.damage_shield == 18
    assert thorns_dps(rank6, 312, 0.168, 1.0) == pytest.approx(70.416)
    assert thorns_dps(rank6, 312, 0.0, 1.5) == pytest.approx(27.0)
    assert thorns_dps(None, 312, 0.168, 1.0) == 0.0


def test_druid_side_returns_thorns_against_melee_by_default_without_scaling():
    side = class_side("druid", TABLE.at(60), CLS.spells, CLS, ranks("druid-balance-pvp"))
    assert side.nova_dps == pytest.approx(18.0)        # coefficient 0 (client data), 1 hit per second


def test_with_scaling_on_balance_gains_and_feral_does_not():
    balance = class_side("druid", TABLE.at(60), CLS.spells, CLS, ranks("druid-balance-pvp"), assumptions=ON)
    feral = class_side("druid", TABLE.at(60), CLS.spells, CLS, ranks("druid-feral"), assumptions=ON)
    assert balance.nova_dps == pytest.approx(70.416)
    assert feral.nova_dps == pytest.approx(18.0)       # the feral row carries no spell power


def test_at_the_beta_cap():
    balance = class_side("druid", TABLE.at(30), CLS.spells, CLS, ranks("druid-balance-pvp"), assumptions=ON)
    assert balance.nova_dps == pytest.approx(24.624)


def test_the_toggle_is_registered_with_the_client_value_as_default():
    a = Assumptions.load()
    assert a["thorns_spell_power_coefficient"] == 0.0
    assert a.entries["thorns_spell_power_coefficient"].options == (0.0, 0.168)
