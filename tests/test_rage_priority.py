"""Rage priority (#424): Overpower (5 Rage) and Rend (10 Rage per 21 s) do the most damage per Rage, so they get
Rage first; Mortal Strike, Bloodthirst, Whirlwind and Slam take what's left, then Heroic Strike. Before, Mortal
Strike spent all of Arms' Rage at 60 against a boss and Overpower and Rend never fired."""

import pytest

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.warrior_rotation import warrior_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import Attacker, Target, land_chance
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

W = class_module("warrior")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("warrior"), W.TALENT_EFFECTS, W.UNMODELED)
STATS = MeleeStatTable.load("warrior").at(60)
BOSS = Target(3, 3731)
ARMS = next(b for b in load_builds(class_name="warrior") if b.id == "warrior-arms").final_ids(CLS)


def total(kind, applies):
    return sum(e.values[ARMS[t.talent_id] - 1] for t in CLS.talents if ARMS.get(t.talent_id, 0) > 0
               for e in t.effects if e.kind == kind and applies in e.applies_to)


def test_overpower_and_rend_come_first():
    r = warrior_rotation(STATS, CLS.spells, CLS, ARMS, BOSS)
    parts = dict(r.parts)
    assert [n for n, _ in r.parts][:3] == ["Overpower", "Rend", "Mortal Strike"]
    assert parts["Overpower"] > 0 and parts["Mortal Strike"] > 0


def test_rend_is_kept_up_in_full():
    rend = best_rank(CLS.spells, "Rend", 60)
    attacker = Attacker(60, STATS.attack_power, STATS.crit_pct + total("crit_chance", "all"),
                        STATS.hit_pct + total("hit_chance", "all"))
    expected = (rend.periodic_damage / rend.duration * land_chance(attacker, BOSS)
                * (1 + total("damage_pct", "Rend") / 100))
    assert dict(warrior_rotation(STATS, CLS.spells, CLS, ARMS, BOSS).parts)["Rend"] == pytest.approx(expected)


def test_arms_gains():
    # the same build, Overpower and Rend taken out of the spell list, loses damage
    without = [s for s in CLS.spells if s.name not in ("Overpower", "Rend")]
    assert (warrior_rotation(STATS, CLS.spells, CLS, ARMS, BOSS).dps
            > warrior_rotation(STATS, without, CLS, ARMS, BOSS).dps)
