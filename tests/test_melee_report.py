"""Scored rogue and hunter reports (#133): optimized leveling orders, PvE scores per checkpoint,
and model picks; PvP slots are scored with the duel model from the class's side (#134)."""

from pathlib import Path

import pytest

from wowforever.schema import latest_dataset_path
from wowforever.report import report_from_dataset
from wowforever.rules import check_order
from wowforever.schema import Dataset

pytestmark = pytest.mark.slow

DATASET = latest_dataset_path()


@pytest.fixture(scope="module", params=["rogue", "hunter"])
def report(request):
    return request.param, report_from_dataset(DATASET, request.param)


def test_builds_get_legal_optimized_orders_and_pve_scores(report):
    class_name, r = report
    cls = Dataset.load(DATASET).class_data(class_name)
    assert r["engine"] is True and r["class"] == class_name
    for b in r["builds"]:
        assert check_order(cls, b["order"]) == [], b["id"]
        if b["mode"] == "leveling":   # questing pace only (owner request, 2026-10-07)
            assert set(b["scores"]) == {"questing"} and all(row["score"] > 0 for row in b["scores"]["questing"].values())
            continue
        assert b["order_source"] in ("hand-written", "optimized for questing kills/hour")
        pvp = {"wpvp_melee", "wpvp_melee_they_open", "wpvp_caster", "stealth_ambush", "battleground",
               "survival", "control"}                                       # every class's PvP rows (#323)
        assert set(b["scores"]) == {"questing", "dungeon", "raid", "aoe", "outnumbered"} | pvp   # #263, #287
        assert all(set(b["scores"][k]) == {20, 30, 40, 50, 60} for k in pvp)
        assert all(0 <= row["score"] <= 1 for k in pvp for row in b["scores"][k].values())
        assert set(b["scores"]["outnumbered"]) == {20, 30, 40, 50, 60}
        assert all(0 <= row["score"] <= 1 and row["unit"] == "2v1 0-1" for row in b["scores"]["outnumbered"].values())
        assert set(b["scores"]["questing"]) == {20, 30, 40, 50, 60} and set(b["scores"]["raid"]) == {60}
        assert set(b["scores"]["aoe"]) == {20, 30, 40, 50, 60}
        assert all(row["lower_better"] and row["unit"] == "seconds (3-mob pack)" for row in b["scores"]["aoe"].values())
        assert all(row["score"] > 0 for name, rows in b["scores"].items() if name not in pvp for row in rows.values())


def test_pve_and_pvp_slots_are_scored(report):
    _, r = report
    for s in r["shortlist"]:
        if s["standard"]:
            assert s["standard_score"] > 0
            if s["focus"] == "PvP":
                assert 0 < s["standard_score"] < 1          # mean duel score (#134)
    assert any("#134" in c for c in r["caveats"])
