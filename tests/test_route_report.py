"""Routes-only report for classes the calculator can't score yet (#105): community builds become
legal point orders for the tracker, placed in the archetype x focus matrix without scores."""

from pathlib import Path

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.report import report_from_dataset, route_report
from wowforever.rules import check_order
from wowforever.schema import Dataset

DATASET = Path(__file__).resolve().parents[1] / "data" / "datasets" / "1.60.1.70205.json"
REPORT = report_from_dataset(DATASET, "rogue")


def test_only_the_mage_has_a_scoring_engine():
    assert class_module("mage").ENGINE is True
    assert getattr(class_module("rogue"), "ENGINE", False) is False


def test_rogue_report_is_routes_only():
    assert REPORT["class"] == "rogue" and REPORT["engine"] is False
    ids = {b["id"] for b in REPORT["builds"]}
    assert ids == {b.id for b in load_builds(class_name="rogue")}
    for b in REPORT["builds"]:
        assert b["scores"] == {} and b["sensitivity"] == []
        assert b["order_source"].startswith("legal order")
    assert any("#111" in c for c in REPORT["caveats"])


def test_route_orders_are_legal_and_spend_the_build():
    ds = Dataset.load(DATASET)
    cls = ds.class_data("rogue")
    builds = {b.id: b for b in load_builds(class_name="rogue")}
    for b in REPORT["builds"]:
        assert check_order(cls, b["order"]) == [], b["id"]
        assert sorted(b["order"]) == sorted(t for t, r in builds[b["id"]].final_ids(cls).items() for _ in range(r))


def test_matrix_slots_cover_every_tree_and_recognized_hybrid():
    slots = [(s["archetype"], s["focus"]) for s in REPORT["shortlist"]]
    archetypes = list(dict.fromkeys(a for a, _ in slots))
    assert archetypes == ["deep Assassination", "deep Combat", "deep Subtlety", "Assassination/Subtlety"]
    assert all({(a, "PvP"), (a, "PvE")} <= set(slots) for a in archetypes)
    by_slot = {(s["archetype"], s["focus"]): s for s in REPORT["shortlist"]}
    assert by_slot[("deep Combat", "PvE")]["standard"] == "rogue-combat"
    assert by_slot[("deep Combat", "PvP")]["standard"] == "rogue-combat-pvp"
    assert by_slot[("deep Assassination", "PvE")]["standard"] == "rogue-mutilate"
    assert by_slot[("Assassination/Subtlety", "PvP")]["standard"] == "rogue-subtlety"
    assert by_slot[("deep Subtlety", "PvE")]["standard"] is None
    assert all(s["standard_score"] is None and s["model_pick"] is None for s in REPORT["shortlist"])


def test_route_report_is_also_callable_directly():
    assert callable(route_report)


def test_mage_report_keeps_its_engine():
    # the mage path is unchanged apart from the class/engine keys
    assert class_module("mage").ENGINE is True
