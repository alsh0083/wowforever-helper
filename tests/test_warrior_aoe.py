"""Warrior against a pack (#262, warrior slice): warrior_rotation(..., pack=N) sums damage over N mobs.

- Whirlwind and Thunder Clap hit min(pack, MaxTargets) mobs; the data gives both MaxTargets 4.
- Thunder Clap joins the rotation only against a pack (flat 103 damage at rank 6, through the combat table).
- Against a pack, abilities go in order of damage per Rage over all the mobs, so Whirlwind comes before
  Mortal Strike; single target keeps Mortal Strike first.
- Cleave (config cleave_targets 2, Classic) takes Heroic Strike's place on the next swing.
- Sweeping Strikes (talent): once per cooldown, its 5 attacks (rank text) each hit a second mob for an
  average attack's damage.
Hand-worked scaling for Fury PvE at 60 against questing mobs (3300 armor), where Rage covers Whirlwind
(1 per 10 s) at every pack size: Whirlwind's part is 3x the single-target part at 3 mobs and 4x at 5
(cap 4); Thunder Clap's part goes 3 : 4 from 3 to 5 mobs (same Rage left after Whirlwind, same rate).
melee_scenarios.aoe for a warrior: 3 x mob health / the class engine's output(..., pack=3).dps, labelled with the
abilities that hit several mobs.
"""

import pytest

from wowforever.classes import engine
from wowforever import melee_scenarios as ms
from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes import warrior_rotation as wr
from wowforever.effects import attach_effects
from wowforever.physical import Target
from wowforever.scenarios import default_params
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warrior")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("warrior"), W.TALENT_EFFECTS, W.UNMODELED)
BUILDS = {b.id: b for b in load_builds(class_name="warrior")}
STATS = ms.stat_table("warrior").at(60)
MOBS = Target(0, 3300)


def rotation(build_id, pack, **kw):
    return wr.warrior_rotation(STATS, CLS.spells, CLS, BUILDS[build_id].final_ids(CLS), MOBS, pack=pack, **kw)


def test_single_target_is_unchanged():
    one = rotation("warrior-fury-pve", 1)
    default = wr.warrior_rotation(STATS, CLS.spells, CLS, BUILDS["warrior-fury-pve"].final_ids(CLS), MOBS)
    assert one == default
    assert one.aoe == () and [n for n, _ in one.parts] == ["Whirlwind", "Heroic Strike"]


def test_whirlwind_hits_up_to_four_mobs():
    one, three, five = (dict(rotation("warrior-fury-pve", p).parts) for p in (1, 3, 5))
    assert three["Whirlwind"] == pytest.approx(3 * one["Whirlwind"])
    assert five["Whirlwind"] == pytest.approx(4 * one["Whirlwind"])


def test_thunder_clap_joins_against_a_pack():
    three, five = (dict(rotation("warrior-fury-pve", p).parts) for p in (3, 5))
    assert "Thunder Clap" not in dict(rotation("warrior-fury-pve", 1).parts)
    assert three["Thunder Clap"] > 0
    assert three["Thunder Clap"] / five["Thunder Clap"] == pytest.approx(3 / 4)


def test_heroic_strike_gives_way_to_cleave():
    for p in (2, 3):
        assert "Heroic Strike" not in rotation("warrior-fury-pve", p).abilities


def test_arms_whirls_before_mortal_strike_against_a_pack():
    assert rotation("warrior-arms", 1).abilities[0] == "Mortal Strike"
    assert rotation("warrior-arms", 3).abilities[0] == "Whirlwind"
    assert rotation("warrior-arms", 3).dps > rotation("warrior-arms", 1).dps


def test_sweeping_strikes_with_rage_to_spare(monkeypatch):
    real = wr.load_toml
    monkeypatch.setattr(wr, "load_toml", lambda path: {**real(path), "bloodrage_rage": 5000.0})
    three = rotation("warrior-arms", 3)
    assert "Sweeping Strikes" in three.aoe and dict(three.parts)["Sweeping Strikes"] > 0
    assert "Cleave" in three.aoe
    assert "Sweeping Strikes" not in rotation("warrior-arms", 1).abilities


def test_aoe_pull_runs_the_rotation_against_the_pack():
    ranks = BUILDS["warrior-fury-pve"].final_ids(CLS)
    out = engine("warrior").output(STATS, CLS.spells, CLS, ranks, MOBS, pack=3)
    seconds, label = ms.aoe("warrior", STATS, CLS.spells, CLS, ranks)
    assert seconds == pytest.approx(3 * default_params("aoe", 60).mob_hp / out.dps)
    assert label == "Whirlwind, Thunder Clap"
