"""The report layer on real fixture data: every build gets a legal order that respects its
must-have levels, scores at each checkpoint, and the payload is JSON-serializable."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.classes.mage import LAYOUT, SKILL_LINES, TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells
from wowforever.report import CHECKPOINTS, build_report, ranks_at
from wowforever.rules import check_order
from wowforever.sources.wowforevertalent import parse_page
from wowforever.stats import StatTable

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def payload():
    cls, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205"), LAYOUT,
                             parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                             wago_build="1.60.1.70205")
    cls, _ = attach_effects(cls, TALENT_EFFECTS, UNMODELED)
    spells = class_spells(read_tables(FIX / "wago-1.60.1.70205-spells"), skill_lines=SKILL_LINES)
    cls = replace(cls, spells=spells)
    report = build_report(cls, spells, load_builds(class_name="mage"), StatTable.load("mage"), Assumptions.load(),
                          {"version": "1.60.1.70205", "game_build": "1.60.1.70205"})
    return cls, report


def test_payload_is_json_serializable(payload):
    _, report = payload
    json.dumps(report)


def test_every_build_has_a_legal_order_meeting_its_deadlines(payload):
    cls, report = payload
    for b in report["builds"]:
        assert check_order(cls, b["order"]) == [], b["id"]
        for name, level in b["must_have_by"].items():
            t = cls.talent_named(name)
            assert ranks_at(b["order"], level, cls).get(t.talent_id, 0) == t.max_rank, (b["id"], name)


def test_elementalist_variants_keep_their_hand_written_orders(payload):
    _, report = payload
    hand = [b for b in report["builds"] if b["id"].startswith("elementalist")]
    assert len(hand) == 1 and all(b["order_source"] == "hand-written" and b["open_points"] == 0 for b in hand)
    others = [b for b in report["builds"] if not b["id"].startswith("elementalist")]
    assert all(b["order_source"].startswith("optimized") and b["open_points"] == 0 for b in others)


def test_scores_at_each_checkpoint(payload):
    _, report = payload
    for b in report["builds"]:
        assert set(b["scores"]["questing"]) == set(CHECKPOINTS)
        assert all(v["score"] > 0 for v in b["scores"]["questing"].values())
        assert set(b["scores"]["raid"]) == {60}
        assert set(b["scores"]["survival"]) == set(CHECKPOINTS) == set(b["scores"]["control"])
        for scenario in ("wpvp_melee", "wpvp_melee_they_open", "wpvp_caster", "stealth_ambush", "battleground"):
            assert set(b["scores"][scenario]) == set(CHECKPOINTS)
            assert all(0 <= v["score"] <= 1 for v in b["scores"][scenario].values())
        assert all(0 <= v["score"] <= 1 for v in b["scores"]["survival"].values())


def test_talents_and_milestones_for_the_dashboard(payload):
    _, report = payload
    assert len(report["talents"]) == 54
    ignite = next(t for t in report["talents"].values() if t["name"] == "Ignite")
    assert ignite["icon"] == "spell_fire_incinerate" and len(ignite["rank_text"]) == 5
    assert {"level": 40, "spell": "Frostfire Bolt", "rank": 1} in report["spell_milestones"]
    taught = {(m["spell"], m["rank"]) for m in report["spell_milestones"]}
    assert not {s for s, _ in taught} & {"Ice Block", "Presence of Mind", "Arcane Power", "Cold Snap"}
    assert ("Ice Lance", 2) in taught and ("Ice Lance", 1) not in taught     # talent grants rank 1


def test_report_cli_from_a_saved_dataset(payload, tmp_path, capsys):
    from wowforever.__main__ import main
    from wowforever.schema import Dataset, Provenance
    cls, _ = payload
    prov = Provenance("wago.tools", "1.60.1.70205", "1.60.1.70205", "2026-10-04T00:00:00Z", "0" * 64)
    Dataset("1.60.1.70205", "1.60.1.70205", (cls,), (prov,)).save(tmp_path / "ds.json")
    assert main(["report", "--dataset", str(tmp_path / "ds.json"), "--out", str(tmp_path / "r.json")]) == 0
    report = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert report["dataset"]["game_build"] == "1.60.1.70205" and len(report["builds"]) == len(load_builds(class_name="mage"))


def test_shortlist_in_payload(payload):
    _, report = payload
    slots = {(s["archetype"], s["focus"]): s for s in report["shortlist"]}
    assert len(slots) == 10                                  # 3 deep + 2 hybrids, x PvP/PvE
    ff = slots[("Fire/Frost", "PvE")]
    assert ff["standard"] == "fire-frost-shatter" and "elementalist-pve-v2" in ff["candidates"]
    for s in report["shortlist"]:
        if s["model_pick"]:
            assert s["model_pick_changes"] and sum(s["model_pick"].values()) == 51
