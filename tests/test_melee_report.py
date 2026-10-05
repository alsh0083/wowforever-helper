"""Scored rogue and hunter reports (#133): optimized leveling orders, PvE scores per checkpoint,
and PvE model picks; PvP cells keep the community standard without a score until #134."""

from pathlib import Path

import pytest

from wowforever.report import report_from_dataset
from wowforever.rules import check_order
from wowforever.schema import Dataset

DATASET = Path(__file__).resolve().parents[1] / "data" / "datasets" / "1.60.1.70205.json"


@pytest.fixture(scope="module", params=["rogue", "hunter"])
def report(request):
    return request.param, report_from_dataset(DATASET, request.param)


def test_builds_get_legal_optimized_orders_and_pve_scores(report):
    class_name, r = report
    cls = Dataset.load(DATASET).class_data(class_name)
    assert r["engine"] is True and r["class"] == class_name
    for b in r["builds"]:
        assert check_order(cls, b["order"]) == [], b["id"]
        assert b["order_source"] in ("hand-written", "optimized for questing kills/hour")
        assert set(b["scores"]) == {"questing", "dungeon", "raid"}
        assert set(b["scores"]["questing"]) == {20, 30, 40, 50, 60} and set(b["scores"]["raid"]) == {60}
        assert all(row["score"] > 0 for rows in b["scores"].values() for row in rows.values())


def test_pve_slots_are_scored_and_pvp_slots_wait_for_134(report):
    _, r = report
    for s in r["shortlist"]:
        if s["focus"] == "PvP":
            assert s["standard_score"] is None and s["model_pick"] is None
        elif s["standard"]:
            assert s["standard_score"] > 0
    assert any("#134" in c for c in r["caveats"])
