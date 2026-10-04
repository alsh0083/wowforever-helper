"""Tests for the cross-source consistency check (#12)."""

from pathlib import Path

from wowforever.classes.mage import LAYOUT
from wowforever.crosscheck import crosscheck
from wowforever.normalize import normalize_class, read_tables
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
TABLES = read_tables(FIX / "wago-1.60.1.70205")
HTML = (FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")


def run(html=HTML, wago_build="1.60.1.70205"):
    page = parse_page(html)
    cls, report = normalize_class(TABLES, LAYOUT, page, wago_build=wago_build)
    return crosscheck(cls, page, report, wago_build=wago_build)


def test_current_sources_only_differ_by_build_lag():
    result = run()
    assert result.lagging_source == "wowforevertalent.com"
    assert result.problems == []
    assert "1.60.1.70170" in result.summary() and "1.60.1.70205" in result.summary()


def test_matching_builds_and_data_are_clean():
    result = run(wago_build="1.60.1.70170")
    assert result.lagging_source is None
    assert result.problems == [] and result.ok
    assert result.summary() == "Sources agree."


def test_max_rank_disagreement_is_flagged():
    # the page says Impact has 4 ranks; wago says 3
    page = parse_page(HTML)
    fire = page.trees[1]
    impact = next(t for t in fire["talents"] if t["name"] == "Impact")
    impact["maxRank"] = 4
    cls, report = normalize_class(TABLES, LAYOUT, page, wago_build="1.60.1.70205")
    result = crosscheck(cls, page, report, wago_build="1.60.1.70205")
    assert any("Impact" in p and "max rank" in p and "3" in p and "4" in p for p in result.problems)


def test_prerequisite_disagreement_is_flagged():
    page = parse_page(HTML)
    frost = page.trees[2]
    barrier = next(t for t in frost["talents"] if t["name"] == "Ice Barrier")
    barrier["prerequisite"] = None
    cls, report = normalize_class(TABLES, LAYOUT, page, wago_build="1.60.1.70205")
    result = crosscheck(cls, page, report, wago_build="1.60.1.70205")
    assert any("Ice Barrier" in p and "prerequisite" in p for p in result.problems)


def test_normalize_report_problems_are_carried_over():
    page = parse_page(HTML)
    page.trees[1]["talents"] = [t for t in page.trees[1]["talents"] if t["name"] != "Ignite"]
    cls, report = normalize_class(TABLES, LAYOUT, page, wago_build="1.60.1.70205")
    result = crosscheck(cls, page, report, wago_build="1.60.1.70205")
    assert any("Ignite" in p for p in result.problems)
