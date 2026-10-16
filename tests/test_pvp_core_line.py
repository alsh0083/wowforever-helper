"""Golden tests for the PvP core-talent line (#341).

The PvP score adds CONSENSUS_BONUS (0.10) x the share of the class's core talents taken (#315, #320).
Core lists (config/consensus.toml): warrior Mortal Strike + Improved Hamstring; mage Cold Snap,
Ice Barrier, Ice Block, Improved Frost Nova, Permafrost; hunter none.
Hand-worked: warrior with Mortal Strike only -> 1/2 -> 0.05; mage with three of five -> 0.06.
"""

from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.consensus import Consensus
from wowforever.effects import attach_effects
from wowforever.focus import pvp_core_line
from wowforever.report import add_pvp_core
from wowforever.schema import Dataset, latest_dataset_path

DATASET = Dataset.load(latest_dataset_path())
CONSENSUS = Consensus.load()


def loaded(name):
    m = class_module(name)
    cls, _ = attach_effects(DATASET.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)
    return cls


def ids(cls, *names):
    return {cls.talent_named(n).talent_id: 1 for n in names}


def test_warrior_half_the_core_talents():
    cls = loaded("warrior")
    line = pvp_core_line(cls, CONSENSUS, "warrior", ids(cls, "Mortal Strike"))
    assert line == {"taken": ["Mortal Strike"], "missing": ["Improved Hamstring"], "bonus": 0.05}


def test_none_taken_still_shows_the_line():
    line = pvp_core_line(loaded("warrior"), CONSENSUS, "warrior", {})
    assert line == {"taken": [], "missing": ["Improved Hamstring", "Mortal Strike"], "bonus": 0.0}


def test_mage_three_of_five():
    cls = loaded("mage")
    line = pvp_core_line(cls, CONSENSUS, "mage", ids(cls, "Ice Block", "Cold Snap", "Ice Barrier"))
    assert line["taken"] == ["Cold Snap", "Ice Barrier", "Ice Block"]
    assert line["missing"] == ["Improved Frost Nova", "Permafrost"]
    assert line["bonus"] == pytest.approx(0.06)


def test_a_rank_of_zero_is_not_taken():
    cls = loaded("warrior")
    ranks = {cls.talent_named("Mortal Strike").talent_id: 0}
    assert pvp_core_line(cls, CONSENSUS, "warrior", ranks)["taken"] == []


def test_class_without_tiers_has_no_line():
    assert pvp_core_line(loaded("hunter"), CONSENSUS, "hunter", {}) is None


def test_report_builds_get_the_line_at_max_level():
    cls = loaded("warrior")
    ms = cls.talent_named("Mortal Strike").talent_id
    report = {"builds": [{"id": "a", "order": [ms]}, {"id": "b", "order": []}]}
    add_pvp_core("warrior", cls, report)
    assert report["builds"][0]["pvp_core"]["taken"] == ["Mortal Strike"]
    assert report["builds"][1]["pvp_core"]["bonus"] == 0.0


def test_report_builds_of_a_class_without_tiers_get_nothing():
    report = {"builds": [{"id": "a", "order": []}]}
    add_pvp_core("hunter", loaded("hunter"), report)
    assert "pvp_core" not in report["builds"][0]


def test_dashboard_renders_the_line():
    template = (Path(__file__).resolve().parents[1] / "dashboard" / "template.html").read_text(encoding="utf-8")
    assert "build.pvp_core" in template
    assert "Community PvP talents" in template
