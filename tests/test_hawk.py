"""Aspect of the Hawk (#388): its ranged attack power (aura 124) comes from the client data and the ranged hunter
keeps it up. Hand values from SpellEffect of build 1.60.1.70425: rank 1 (13165) 20, rank 6 (14322) 55,
rank 7 (25296) 120."""

from dataclasses import replace
from pathlib import Path

import pytest

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.classes.hunter_rotation import hunter_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

ROOT = Path(__file__).resolve().parents[1]
H = class_module("hunter")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("hunter"), H.TALENT_EFFECTS, H.UNMODELED)


def test_saved_dataset_has_hawk_attack_power():
    hawk = {s.rank: s.ranged_attack_power for s in CLS.spells if s.name == "Aspect of the Hawk"}
    assert (hawk[1], hawk[6], hawk[7]) == (20.0, 55.0, 120.0)
    assert best_rank(CLS.spells, "Aimed Shot", 60).ranged_attack_power == 0.0


@pytest.mark.skipif(not (ROOT / "data" / "cache" / "wago" / "1.60.1.70425").is_dir(), reason="client tables not cached")
def test_normalizer_reads_aura_124():
    from wowforever.normalize import read_tables
    from wowforever.normalize_spells import class_spells

    spells = class_spells(read_tables(ROOT / "data" / "cache" / "wago" / "1.60.1.70425"), skill_lines=H.SKILL_LINES)
    assert best_rank(spells, "Aspect of the Hawk", 60).ranged_attack_power == 120.0


def test_rotation_adds_the_best_known_rank():
    ranks = {b.id: b.final_ids(CLS) for b in load_builds(class_name="hunter")}["hunter-marksmanship"]
    stats = stat_table("hunter").at(60)
    no_hawk = [s for s in CLS.spells if s.name != "Aspect of the Hawk"]
    with_hawk = hunter_rotation(stats, CLS.spells, CLS, ranks, Target(3, 0))
    by_hand = hunter_rotation(replace(stats, ranged_attack_power=stats.ranged_attack_power + 120), no_hawk, CLS,
                              ranks, Target(3, 0))
    assert with_hawk.dps == pytest.approx(by_hand.dps)
    assert with_hawk.dps > hunter_rotation(stats, no_hawk, CLS, ranks, Target(3, 0)).dps
