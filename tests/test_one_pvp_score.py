"""One PvP score for every class (#315 option 1, #323): the mean of the four world-PvP duels and the
battleground, plus CONSENSUS_BONUS x the share of the class's core talents taken.

Golden: duels 0.4, 0.5, 0.6, 0.3 and battleground 0.5 -> mean 2.3 / 5 = 0.46; 1 of 2 core talents
taken -> + 0.10 x 1/2 = 0.05 -> 0.51. No core talents (a class without tiers) -> 0.46.
"""

import pytest

from wowforever import focus
from wowforever.consensus import Consensus

DUELS = {"wpvp_melee": 0.4, "wpvp_melee_they_open": 0.5, "wpvp_caster": 0.6, "stealth_ambush": 0.3}


@pytest.fixture
def fixed(monkeypatch):
    monkeypatch.setattr(focus, "best_scenario_scores", lambda sides, kits: {k: {"score": v} for k, v in DUELS.items()})
    monkeypatch.setattr(focus, "best_side_battleground", lambda sides, level, consensus: {"score": 0.5})


def test_duels_battleground_and_bonus(fixed):
    c = Consensus.load()
    assert focus.side_pvp_score([], [], 60, {1, 2}, {1: 1}, c) == pytest.approx(0.51)
    assert focus.side_pvp_score([], [], 60, set(), {1: 1}, c) == pytest.approx(0.46)
    assert focus.side_pvp_score([], [], 60, {1, 2}, {}, c) == pytest.approx(0.46)


def test_core_talents_come_from_the_class_s_own_tiers():
    from wowforever.schema import Dataset, latest_dataset_path

    data, c = Dataset.load(latest_dataset_path()), Consensus.load()
    warrior = data.class_data("warrior")
    names = {t.talent_id: t.name for t in warrior.talents}
    assert {names[i] for i in focus.core_talent_ids(warrior, c, "warrior")} == {"Mortal Strike", "Improved Hamstring"}
    assert focus.core_talent_ids(data.class_data("hunter"), c, "hunter") == set()
