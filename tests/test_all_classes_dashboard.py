"""All nine classes on the dashboard (planning round 2: #155-#161): community standards and
routes for the six new classes, their themes, and copy that follows the class."""

import json
import re
from pathlib import Path

import pytest

from wowforever.builds import load_builds
from wowforever.classes import CLASSES, class_module
from wowforever.dashboard import CLASS_THEMES, TREE_COLORS, _school_style, render

DATA = Path(__file__).resolve().parents[1] / "data"
NEW = ("warrior", "druid", "paladin", "priest", "shaman", "warlock")
# in-game class colors
ACCENTS = {"warrior": "#C69B6D", "druid": "#FF7C0A", "paladin": "#F48CBA", "priest": "#FFFFFF",
           "shaman": "#0070DD", "warlock": "#8788EE"}


def report(name):
    return json.loads((DATA / f"report-{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", NEW)
def test_theme_uses_the_class_color_and_its_own_trees(name):
    theme = CLASS_THEMES[name]
    assert theme["accent"] == ACCENTS[name] and theme["crest"].startswith("<svg")
    assert list(theme["trees"]) == [t["name"] for t in report(name)["trees"]]
    for css in theme["trees"].values():
        assert css.startswith(f"{name}-") and css in TREE_COLORS


def test_tree_css_names_are_unique_across_classes():
    names = [css for t in CLASS_THEMES.values() for css in t["trees"].values()]
    assert len(names) == len(set(names))


def test_matrix_bars_use_the_class_trees():
    # Holy, Protection and Restoration repeat across classes
    assert _school_style("deep Holy", "paladin") == "--from:var(--paladin-holy);--to:var(--paladin-holy)"
    assert _school_style("deep Holy", "priest") == "--from:var(--priest-holy);--to:var(--priest-holy)"
    assert _school_style("deep Restoration", "shaman").startswith("--from:var(--shaman-restoration)")


@pytest.mark.parametrize("name", [c for c in NEW if not getattr(class_module(c), "ENGINE", False)])
def test_routes_only_reports_carry_standards_and_their_own_note(name):
    r = report(name)
    assert r["engine"] is False and r["scoring_note"] == class_module(name).SCORING_NOTE
    assert "melee and ranged" not in r["scoring_note"]
    standards = {s["standard"] for s in r["shortlist"] if s["standard"]}
    assert standards == {b.id for b in load_builds(class_name=name)}
    assert all(b["order"] and "#111" not in b["order_source"] for b in r["builds"])


def test_dashboard_lists_every_class_in_registry_order():
    payloads = [json.loads((DATA / "report.json").read_text(encoding="utf-8"))] + [report(c) for c in CLASSES if c != "mage"]
    html = render(payloads, {})
    assert re.findall(r'data-class-tab="(\w+)"', html) == list(CLASSES)
    assert "DATA.scoring_note" in html and "melee and ranged model" not in html
