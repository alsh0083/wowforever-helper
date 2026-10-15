"""Rogue against a pack (#262, rogue slice): rogue_rotation(..., pack=N) sums damage over N mobs.

Blade Flurry (talent): "your melee attacks strike an additional nearby opponent. Lasts 15 sec."; data
cooldown 120 s. Against a pack of 2 or more, every attack hits a second mob for 15 / 120 of the time,
averaged over the fight like its haste: pack DPS = single-target DPS x (1 + 15/120) = x 1.125, white and
yellow alike. Without the talent, or against one mob, nothing changes.
"""

import pytest

from wowforever.classes import engine
from wowforever import melee_scenarios as ms
from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.rogue_rotation import rogue_rotation
from wowforever.effects import attach_effects
from wowforever.physical import Target
from wowforever.scenarios import default_params
from wowforever.schema import Dataset, latest_dataset_path

R = class_module("rogue")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("rogue"), R.TALENT_EFFECTS, R.UNMODELED)
BUILDS = {b.id: b for b in load_builds(class_name="rogue")}
STATS = ms.stat_table("rogue").at(60)
MOBS = Target(0, 3300)
COMBAT = BUILDS["rogue-combat"].final_ids(CLS)


def test_blade_flurry_hits_a_second_mob():
    one = rogue_rotation(STATS, CLS.spells, CLS, COMBAT, MOBS)
    for pack in (2, 3):
        many = rogue_rotation(STATS, CLS.spells, CLS, COMBAT, MOBS, pack=pack)
        assert many.dps == pytest.approx(one.dps * 1.125)
        assert (many.white_dps, many.yellow_dps) == (pytest.approx(one.white_dps * 1.125), pytest.approx(one.yellow_dps * 1.125))
        assert many.aoe == ("Blade Flurry",)
    assert one.aoe == ()


def test_without_blade_flurry_a_pack_changes_nothing():
    flurry = CLS.talent_named("Blade Flurry").talent_id
    ranks = {t: r for t, r in COMBAT.items() if t != flurry}
    assert rogue_rotation(STATS, CLS.spells, CLS, ranks, MOBS, pack=3) == rogue_rotation(STATS, CLS.spells, CLS, ranks, MOBS)


def test_aoe_pull_uses_blade_flurry():
    out = engine("rogue").output(STATS, CLS.spells, CLS, COMBAT, MOBS, pack=3)
    assert ms.aoe("rogue", STATS, CLS.spells, CLS, COMBAT) == (pytest.approx(3 * default_params("aoe", 60).mob_hp / out.dps),
                                                              "Blade Flurry")
