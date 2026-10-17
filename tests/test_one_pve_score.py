"""One PvE score for every class (#317, part B).

The mage's PvE goes through `melee_scenarios.pve_score` like every class. Its raid, dungeon and AoE
parts are the mage's own models (part A made the shared raid the mage's raid; dungeon and AoE
already were). Questing is the shared one, which adds health downtime the mage's never counted:
the one intended change (at most -5% questing, -0.8% PvE on today's builds).
"""

import inspect
from pathlib import Path

import pytest

from wowforever import focus, group, report
from wowforever import melee_scenarios as ms
from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.scenarios import Character, aoe_curve, default_params, raid
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.stats import StatTable

DATASET = Dataset.load(latest_dataset_path())
m = class_module("mage")
CLS, _ = attach_effects(DATASET.class_data("mage"), m.TALENT_EFFECTS, m.UNMODELED)
STATS = StatTable.load("mage").at(60)
BUILDS = {b.id: b.final_ids(CLS) for b in load_builds(class_name="mage") if b.mode != "leveling"}


def test_the_mage_only_score_functions_are_gone():
    for name in ("pve_score_fn", "pvp_score_fn", "PVE_REFERENCES"):
        assert not hasattr(focus, name), name


def test_stat_table_serves_the_mage():
    assert ms.stat_table("mage").at(60) == STATS


def test_report_has_no_mage_stat_table_branch():
    assert 'StatTable.load("mage")' not in inspect.getsource(report)


# builds without Arcane Blast: its stacks (#355) exist only on the shared path
@pytest.mark.parametrize("build", ["deep-frost", "elementalist-pve-v2", "mage-frost-pve", "fire-frost-shatter"])
def test_mage_pve_is_its_own_models_plus_shared_questing(build):
    ranks, a = BUILDS[build], Assumptions.load()
    char = Character(60, STATS, CLS.spells, CLS, dict(ranks))
    ref = ms._config()["references"]
    expected = (ms.questing("mage", STATS, CLS.spells, CLS, ranks) / ref["questing"]
                + raid(char, default_params("raid", 60), a).score / ref["raid"]
                + group.typical_dungeon_dps("mage", STATS, CLS, ranks) / ref["dungeon"]
                + ref["aoe_seconds"] / aoe_curve(char, default_params("aoe", 60), a).details["aoe_time"][3]) / 4
    assert ms.pve_score("mage", STATS, CLS.spells, CLS, ranks) == pytest.approx(expected, rel=1e-9)
