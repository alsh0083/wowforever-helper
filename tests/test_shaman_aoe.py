"""Enhancement shaman against a pack (#262, shaman slice): enhancement_rotation(..., pack=N).

Against a pack (N > 1), Fire Nova (Forever's 408341..., cooldown 10 s, damage from #261) goes out on
cooldown and hits every mob, rolled like Earth Shock (spell hit and crit at base damage, no spell power
on the melee row): N x hit x average x (1 + crit x 0.5) / cooldown, so its part grows linearly with N.
Against one mob nothing changes. melee_scenarios.aoe for an Enhancement build: 3 x mob health /
the class engine's output(..., pack=3).dps, labelled "Fire Nova"; Elemental builds keep caster.aoe_pull (#260).
"""

import pytest

from wowforever.classes import engine
from wowforever import melee_scenarios as ms
from wowforever.builds import load_builds
from wowforever.caster import aoe_pull
from wowforever.classes import class_module
from wowforever.classes.shaman_rotation import enhancement_rotation
from wowforever.effects import attach_effects
from wowforever.physical import Target
from wowforever.scenarios import default_params
from wowforever.schema import Dataset, latest_dataset_path

S = class_module("shaman")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("shaman"), S.TALENT_EFFECTS, S.UNMODELED)
BUILDS = {b.id: b for b in load_builds(class_name="shaman")}
STATS = ms.stat_table("shaman").at(60)
MOBS = Target(0, 3300)
ENH = BUILDS["shaman-enhancement-pve"].final_ids(CLS)


def rotation(pack):
    return enhancement_rotation(STATS.melee, CLS.spells, CLS, ENH, MOBS, pack=pack)


def test_one_mob_is_unchanged():
    assert rotation(1) == enhancement_rotation(STATS.melee, CLS.spells, CLS, ENH, MOBS)
    assert rotation(1).aoe == ()


def test_fire_nova_hits_every_mob():
    one, two, three = rotation(1), rotation(2), rotation(3)
    per_mob = (two.spell_dps - one.spell_dps) / 2
    assert per_mob > 0
    assert three.spell_dps - one.spell_dps == pytest.approx(3 * per_mob)
    assert (two.white_dps, two.yellow_dps) == (one.white_dps, one.yellow_dps)
    assert two.aoe == three.aoe == ("Fire Nova",)


def test_aoe_pull_for_enhancement_and_elemental():
    out = engine("shaman").output(STATS, CLS.spells, CLS, ENH, MOBS, pack=3)
    mob_hp = default_params("aoe", 60).mob_hp
    assert ms.aoe("shaman", STATS, CLS.spells, CLS, ENH) == (pytest.approx(3 * mob_hp / out.dps), "Fire Nova")
    ele = BUILDS["shaman-elemental"].final_ids(CLS)
    pull = aoe_pull("shaman", STATS.caster, CLS.spells, CLS, ele, 3, mob_hp)
    assert ms.aoe("shaman", STATS, CLS.spells, CLS, ele) == (pytest.approx(pull.seconds), pull.spell)
