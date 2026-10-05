"""In-game test checklist (#31): one item per unknown mechanic, flagged for retest when a patch
touches a talent or spell it involves. Spec: docs/tasks/31-checklist.md."""

from dataclasses import replace

from wowforever.assumptions import Assumptions
from wowforever.checklist import checklist, retest_names
from wowforever.revisions import Change

A = Assumptions.load()


def mark_tested(assumptions, name, text):
    entries = dict(assumptions.entries)
    entries[name] = replace(entries[name], tested=text)
    return Assumptions(entries)


def test_every_assumption_is_an_untested_item_in_config_order():
    items = checklist(A)
    assert [i.name for i in items] == list(A.entries)
    assert all(i.status == "untested" and i.result == "" for i in items)
    ff = next(i for i in items if i.name == "frostfire_ticks_trigger_impact")
    assert ff.talents == ("Frostfire Bolt", "Impact")
    assert ff.question == A.entries["frostfire_ticks_trigger_impact"].why
    assert ff.assumed is False and ff.options == (True, False)


def test_every_assumption_names_what_would_trigger_a_retest():
    assert all(a.talents for a in A.entries.values())


def test_a_tested_item_keeps_its_result():
    a = mark_tested(A, "burning_soul_protects_frostfire", "2026-11-02 on 1.60.2: yes")
    item = next(i for i in checklist(a) if i.name == "burning_soul_protects_frostfire")
    assert item.status == "tested" and item.result == "2026-11-02 on 1.60.2: yes"


def test_a_change_to_an_involved_talent_flags_a_tested_item_for_retest():
    a = mark_tested(A, "burning_soul_protects_frostfire", "2026-11-02 on 1.60.2: yes")
    a = mark_tested(a, "aoe_target_cap", "2026-11-02 on 1.60.2: soft cap at 4")
    changes = [Change("Fire", "Burning Soul", "rank_text", "rank 1 text changed")]
    by_name = {i.name: i for i in checklist(a, changes)}
    assert by_name["burning_soul_protects_frostfire"].status == "retest"
    assert by_name["aoe_target_cap"].status == "tested"            # not involved
    assert by_name["frostfire_ticks_trigger_impact"].status == "untested"  # untested stays untested
    assert retest_names(a, changes) == ["burning_soul_protects_frostfire"]


def test_spell_changes_match_case_insensitively():
    a = mark_tested(A, "aoe_target_cap", "2026-11-02 on 1.60.2: soft cap at 4")
    changes = [Change("", "blizzard", "damage", "damage changed", rank=7)]
    assert retest_names(a, changes) == ["aoe_target_cap"]


def test_report_payload_carries_the_checklist():
    from wowforever.report import build_report
    import inspect
    assert '"checklist"' in inspect.getsource(build_report)


def test_update_summary_lists_retests():
    from wowforever.update import UpdateSummary
    from wowforever.crosscheck import CrosscheckResult
    import dataclasses
    fields = {f.name for f in dataclasses.fields(UpdateSummary)}
    assert "retest" in fields
    src = __import__("inspect").getsource(UpdateSummary.text)
    assert "Retest in game" in src


def test_dashboard_has_the_checklist_section():
    import json
    from pathlib import Path
    from wowforever.dashboard import render
    payload = json.loads((Path(__file__).parent / "fixtures" / "dashboard" / "payload.json").read_text(encoding="utf-8"))
    assert "To test in game" in render(payload, {})
