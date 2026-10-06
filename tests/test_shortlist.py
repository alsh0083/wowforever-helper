"""Tests for the archetype shortlist (#28) on a small synthetic class, with stand-in scores.

Trees: 1 "Arcane", 2 "Fire", 3 "Frost". Every talent has 5 ranks; rows gate at 5 points per row.
Budget is small (rules.max_level 22 -> 13 points) so archetypes use a deep threshold of 9 and a
hybrid threshold of 4 (passed in), mirroring 31/15 at level 60.
"""

import pytest

from wowforever.builds import Build
from wowforever.rules import check_build
from wowforever.schema import ClassData, Rules, Talent, Tree
from wowforever.shortlist import Slot, build_shortlist, classify, improve


def t(tid, tree, row, col):
    return Talent(tid, f"T{tid}", tree, row, col, 5, (), ())


TALENTS = (
    t(1, 1, 0, 0), t(2, 1, 1, 0), t(3, 1, 2, 0),        # Arcane
    t(4, 2, 0, 0), t(5, 2, 0, 1), t(6, 2, 1, 0), t(7, 2, 2, 0),  # Fire
    t(8, 3, 0, 0), t(9, 3, 1, 0), t(10, 3, 2, 0),       # Frost
)
CLS = ClassData("testclass",
                (Tree(1, "Arcane", (1, 2, 3)), Tree(2, "Fire", (4, 5, 6, 7)), Tree(3, "Frost", (8, 9, 10))),
                TALENTS, rules=Rules(first_talent_level=10, max_level=22, points_per_row=5))
TH = dict(deep=9, hybrid=4, recognized=("Fire/Frost",))


def build(bid, final, variant, origin="community"):
    return Build(bid, bid, "", {f"T{k}": v for k, v in final.items()}, variant=variant, origin=origin)


def test_classify_deep_and_hybrid():
    assert classify(CLS, {4: 5, 6: 5, 8: 3}, **TH) == "deep Fire"              # Fire 10
    assert classify(CLS, {4: 5, 8: 5, 9: 3}, **TH) == "Fire/Frost"             # 5 / 8: both >= 4, none >= 9
    assert classify(CLS, {1: 5, 4: 5, 5: 3}, **TH) is None                      # Arcane/Fire not recognized
    assert classify(CLS, {4: 5, 5: 5, 6: 3}, **TH) == "deep Fire"


def fire_value(ranks):
    """Stand-in score: Fire points are worth 1, T7 (Fire row 2) 3 each, everything else 0.1."""
    return sum((3 if tid == 7 else 1 if CLS.talent(tid).tree_id == 2 else 0.1) * r for tid, r in ranks.items())


def test_improve_climbs_legally_and_stays_in_archetype():
    start = {4: 5, 8: 5, 9: 3}                      # Fire/Frost 5/8
    final, score = improve(CLS, start, fire_value, archetype=classify(CLS, start, **TH), **TH)
    assert classify(CLS, final, **TH) == "Fire/Frost"
    assert check_build(CLS, final, level=22) == []
    assert sum(final.values()) == 13
    assert score == pytest.approx(fire_value(final)) and score > fire_value(start)


def test_improve_is_deterministic_and_respects_eval_budget():
    calls = []

    def counted(ranks):
        calls.append(1)
        return fire_value(ranks)

    start = {4: 5, 8: 5, 9: 3}
    a = improve(CLS, start, counted, archetype="Fire/Frost", max_evals=25, **TH)
    assert len(calls) <= 25
    calls.clear()
    assert improve(CLS, start, counted, archetype="Fire/Frost", max_evals=25, **TH) == a


def test_shortlist_slots_standards_model_picks_and_candidates():
    builds = [
        build("std-ff-pve", {4: 5, 8: 5, 9: 3}, "PvE"),              # Fire/Frost PvE standard
        build("std-fire-pvp", {4: 5, 6: 5, 8: 3}, "PvP"),            # deep Fire PvP standard
        build("hand-ff", {4: 5, 8: 5, 9: 3}, "PvE", origin="hand"),  # same as the standard
        build("hand-weak", {8: 5, 9: 5, 10: 3}, "PvE", origin="hand"),  # deep Frost, no standard
    ]
    score_fns = {"PvE": fire_value, "PvP": lambda r: 10.0}         # PvP: everything ties
    slots = build_shortlist(CLS, builds, score_fns, margin=0.05, max_evals=200, **TH)
    by_key = {(s.archetype, s.focus): s for s in slots}

    ff = by_key[("Fire/Frost", "PvE")]
    assert ff.standard == "std-ff-pve"
    assert ff.model_pick is not None and ff.model_pick_score > ff.standard_score * 1.05
    assert ff.candidates["hand-ff"] == pytest.approx(ff.standard_score)
    assert "hand-ff" in ff.qualifying and "std-ff-pve" in ff.qualifying

    fire = by_key[("deep Fire", "PvP")]
    assert fire.standard == "std-fire-pvp" and fire.model_pick is None   # nothing beats a tie by 5%

    frost = by_key[("deep Frost", "PvE")]
    assert frost.standard is None                                        # no community standard
    assert frost.model_pick is not None and "hand-weak" in frost.candidates


def test_slot_is_json_friendly():
    s = Slot("deep Fire", "PvP", "x", 1.0, None, None, {"x": 1.0}, ("x",))
    assert s.as_dict()["archetype"] == "deep Fire"


def test_model_build_holds_a_slot_without_a_community_plan():
    # owner request 2026-10-05: every matrix slot gets a build; model builds are labeled as such
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for path in sorted((root / "data").glob("report*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        origins = {b["id"]: b["origin"] for b in report["builds"]}
        for slot in report["shortlist"]:
            assert slot["standard"], (path.name, slot["archetype"], slot["focus"])
            if origins[slot["standard"]] == "model":
                assert not any(origins[q] == "community" for q in slot["qualifying"])
