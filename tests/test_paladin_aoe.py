"""Paladin against a pack (#262, paladin slice): paladin_rotation(..., pack=N).

Against a pack (N > 1), Consecration is kept down (data: 8 s, no cooldown beyond its duration) and hits
every mob for its base periodic damage (the melee row carries no spell power) with the paladin's Holy
damage talents: N x periodic x (1 + damage %) / max(duration, cooldown), so the Holy part grows by the
same amount per extra mob. Its ticks don't roll the combat table. One mob: unchanged.
melee_scenarios.aoe for Retribution: 3 x mob health / the class engine's output(..., pack=3).dps, labelled
"Consecration".
"""

import pytest

from wowforever.classes import engine
from wowforever import melee_scenarios as ms
from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.paladin_rotation import paladin_rotation
from wowforever.effects import attach_effects
from wowforever.physical import Target
from wowforever.scenarios import default_params
from wowforever.schema import Dataset, latest_dataset_path

P = class_module("paladin")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("paladin"), P.TALENT_EFFECTS, P.UNMODELED)
RET = {b.id: b for b in load_builds(class_name="paladin")}["paladin-retribution"].final_ids(CLS)
STATS = ms.stat_table("paladin").at(60)
MOBS = Target(0, 3300)


def rotation(pack):
    return paladin_rotation(STATS, CLS.spells, CLS, RET, MOBS, pack=pack)


def test_one_mob_is_unchanged():
    assert rotation(1) == paladin_rotation(STATS, CLS.spells, CLS, RET, MOBS)
    assert rotation(1).aoe == () and "Consecration" in rotation(1).abilities      # on one target too (#399)


def test_consecration_hits_every_mob():
    one, two, three = rotation(1), rotation(2), rotation(3)
    per_mob = two.holy_dps - one.holy_dps          # one target already has it (#399)
    assert per_mob > 0
    assert three.holy_dps - one.holy_dps == pytest.approx(2 * per_mob)
    assert two.white_dps == one.white_dps
    assert two.aoe == three.aoe == ("Consecration",)


def test_aoe_pull_uses_consecration():
    out = engine("paladin").output(STATS, CLS.spells, CLS, RET, MOBS, pack=3)
    assert ms.aoe("paladin", STATS, CLS.spells, CLS, RET) == (pytest.approx(3 * default_params("aoe", 60).mob_hp / out.dps),
                                                             "Consecration")
