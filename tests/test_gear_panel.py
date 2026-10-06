"""Recommended gear panel (#190): the page carries the gear data, the class rules and the panel."""

import json
import tomllib
from pathlib import Path

from wowforever.classes import CLASSES
from wowforever.dashboard import compact_gear, render

ROOT = Path(__file__).resolve().parents[1]
GEAR = json.loads((ROOT / "data" / "items" / "gear.json").read_text(encoding="utf-8"))
RULES = tomllib.loads((ROOT / "config" / "gear_rules.toml").read_text(encoding="utf-8"))
MAGE = json.loads((ROOT / "tests" / "fixtures" / "dashboard" / "payload.json").read_text(encoding="utf-8"))


def test_every_class_has_gear_rules():
    assert set(RULES) == set(CLASSES)
    for name, rule in RULES.items():
        assert rule["armor"][0][0] == 1 and all(t in (1, 2, 3, 4) for _, types in rule["armor"] for t in types), name
        assert {"one_hand", "two_hand", "off_hand", "ranged"} <= set(rule), name


def test_compact_gear_keeps_sources_and_faction():
    g = compact_gear(GEAR)
    assert g["checked_at"] == GEAR["checked_at"] and len(g["items"]) == len(GEAR["items"])
    kinds = {s["t"] for it in g["items"] for s in it["src"]}
    assert kinds == {"b", "q", "c"}
    quests = [s for it in g["items"] for s in it["src"] if s["t"] == "q"]
    assert {s["f"] for s in quests} <= {"alliance", "horde", "unknown"}
    assert all("fb" in s for s in quests) and any((s["fb"] or "").startswith("likely") for s in quests)
    assert compact_gear(None) is None


def test_page_has_the_panel_and_the_faction_toggle():
    html = render(MAGE, {}, gear=GEAR, gear_rules=RULES)
    assert 'id="gear-panel"' in html and 'data-faction-pick="horde"' in html
    assert html.index('class="surface level-panel"') < html.index('id="gear-panel"')
    assert "function renderGear()" in html and "renderGear();" in html
    assert "const GEAR = null" not in html and "/*__GEAR__*/" not in html
    # without gear data the panel hides itself
    assert "const GEAR = null" in render(MAGE, {})


def test_boss_drops_carry_no_classic_tag():
    # owner 2026-10-06: a drop listed for a Forever dungeon needs no "Classic drop" note on the page
    assert "Classic drop" not in render(MAGE, {}, gear=GEAR, gear_rules=RULES)


def test_inferred_quest_factions_are_marked_likely():
    html = render(MAGE, {}, gear=GEAR, gear_rules=RULES)
    assert "(likely)" in html and "s.fb" in html
