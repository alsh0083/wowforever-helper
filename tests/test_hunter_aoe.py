"""Hunter against a pack (#262, hunter slice): hunter_rotation(..., pack=N) sums damage over N mobs.

- Multi-Shot hits min(N, multi_shot_targets = 3) mobs (Classic; the data has no count): its part is
  N x one shot's damage / cooldown, so the rotation gains (N - 1) / N of that part.
- A ranged hunter channels Volley back to back instead, when that does more: periodic damage x hit x N /
  duration (every mob).
- Explosive Trap (#268 gives the trap its damage) goes out on cooldown in either mode: average damage x N /
  cooldown, on top of the rotation.
- One mob: unchanged. `parts` holds these abilities' DPS over the pack; `aoe` their names.
Marksmanship at 30 has Multi-Shot only (Volley and Explosive Trap come later); at 60 Volley wins from 3 mobs.
"""

import pytest

from wowforever import melee_scenarios as ms
from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.hunter_rotation import hunter_rotation
from wowforever.effects import attach_effects
from wowforever.physical import Target
from wowforever.scenarios import default_params
from wowforever.schema import Dataset, latest_dataset_path

H = class_module("hunter")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("hunter"), H.TALENT_EFFECTS, H.UNMODELED)
MM = {b.id: b for b in load_builds(class_name="hunter")}["hunter-marksmanship"].final_ids(CLS)
MOBS = Target(0, 3300)


def rotation(level, pack):
    return hunter_rotation(ms.stat_table("hunter").at(level), CLS.spells, CLS, MM, MOBS, pack=pack)


def test_one_mob_is_unchanged():
    stats = ms.stat_table("hunter").at(60)
    assert rotation(60, 1) == hunter_rotation(stats, CLS.spells, CLS, MM, MOBS)
    assert rotation(60, 1).aoe == () and rotation(60, 1).parts == ()


def test_multi_shot_hits_up_to_three_mobs():
    one, two, three, five = (rotation(30, p) for p in (1, 2, 3, 5))
    assert three.aoe == ("Multi-Shot",)
    shot3 = dict(three.parts)["Multi-Shot"]
    assert dict(two.parts)["Multi-Shot"] == pytest.approx(shot3 * 2 / 3)
    assert dict(five.parts)["Multi-Shot"] == pytest.approx(shot3)
    assert three.dps - one.dps == pytest.approx(shot3 * 2 / 3)


def test_volley_and_explosive_trap_hit_every_mob():
    three, five = rotation(60, 3), rotation(60, 5)
    assert three.aoe == five.aoe == ("Volley", "Explosive Trap")
    for name in ("Volley", "Explosive Trap"):
        assert dict(five.parts)[name] == pytest.approx(dict(three.parts)[name] * 5 / 3)
    assert three.ranged_dps == pytest.approx(dict(three.parts)["Volley"])
    assert three.dps == pytest.approx(three.ranged_dps + dict(three.parts)["Explosive Trap"] + three.pet_dps)


def test_aoe_pull_runs_the_rotation_against_the_pack():
    stats = ms.stat_table("hunter").at(60)
    out = ms.rotation_output("hunter", stats, CLS.spells, CLS, MM, MOBS, pack=3)
    assert ms.aoe("hunter", stats, CLS.spells, CLS, MM) == (pytest.approx(3 * default_params("aoe", 60).mob_hp / out.dps),
                                                           "Volley, Explosive Trap")
