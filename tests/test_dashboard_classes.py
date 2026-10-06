"""Multi-class dashboard (#102): one page, a class switcher, and each class's own theme, matrix,
tracker and saves. Structure checks; the look is reviewed by Claude in a browser."""

import json
import re
from pathlib import Path

from wowforever.dashboard import CLASS_THEMES, render

DATA = Path(__file__).resolve().parents[1] / "data"
MAGE = json.loads((Path(__file__).parent / "fixtures" / "dashboard" / "payload.json").read_text(encoding="utf-8"))
ROGUE = json.loads((DATA / "report-rogue.json").read_text(encoding="utf-8"))
HUNTER = json.loads((DATA / "report-hunter.json").read_text(encoding="utf-8"))
HTML = render([MAGE, ROGUE, HUNTER], {})


def test_class_switcher_lists_every_class_with_its_color():
    switcher = re.findall(r'<a class="class-tab" href="\?class=(\w+)"', HTML)
    assert switcher == ["mage", "rogue", "hunter"]
    assert CLASS_THEMES["mage"]["accent"].lower() == "#3fc7eb"
    assert CLASS_THEMES["rogue"]["accent"].lower() == "#fff468"
    assert CLASS_THEMES["hunter"]["accent"].lower() == "#aad372"
    for cls in ("mage", "rogue", "hunter"):
        assert f'body[data-class="{cls}"]' in HTML


def test_each_class_has_its_own_matrix():
    for payload in (MAGE, ROGUE, HUNTER):
        cls = payload.get("class", "mage")
        block = HTML[HTML.index(f'data-class-matrix="{cls}"'):]
        slots = re.findall(r'data-slot="([^"]+)"', block)[:len(payload["shortlist"])]
        assert slots == [f'{s["archetype"]}|{s["focus"]}' for s in payload["shortlist"]]
        for b in payload["builds"]:
            assert f'data-build="{b["id"]}"' in HTML


def test_every_tree_has_a_color_and_talent_card_styles():
    for name, theme in CLASS_THEMES.items():
        assert len(theme["trees"]) == 3
        if name == "mage":
            continue  # the mage's Arcane/Fire/Frost card styles are the template's originals
        for css in theme["trees"].values():
            assert f"--{css}:" in HTML and f".{css} .talent.complete" in HTML


def test_rogue_and_hunter_matrix_rows_use_their_tree_colors():
    assert re.search(r'data-archetype="deep Combat"[^>]*--from:var\(--combat\)', HTML)
    assert re.search(r'data-archetype="Assassination/Subtlety"[^>]*--from:var\(--assassination\)[^"]*--to:var\(--subtlety\)', HTML)
    assert re.search(r'data-archetype="deep Survival"[^>]*--from:var\(--survival\)', HTML)


def test_payloads_are_embedded_for_every_class():
    m = re.search(r"const OTHERS = (\{.*?\});\n", HTML, re.S)
    assert m and set(json.loads(m.group(1))) == {"rogue", "hunter"}


def test_single_payload_still_renders():
    html = render(MAGE, {})
    assert 'data-class-matrix="mage"' in html and "class-tab" in html


def test_talent_layout_previews_the_finished_build():
    # owner request 2026-10-06: a calculator-style grid of the selected build above the journey, shown
    # at max level for a quick preview; the journey below does the per-level allocation
    assert HTML.index('id="talent-layout"') < HTML.index('class="surface level-panel"')
    layout = HTML[HTML.index("function renderLayout(){"):HTML.index("function render(){")]
    assert not any(use in layout for use in ("${level}", "<=level", "p.level"))   # not tied to the slider
    assert "renderLayout();" in HTML[HTML.index("function renderBuild(){"):]
    assert "'taken'" in layout and "'maxed'" in layout and 'class="lt-abbr"' in layout


def test_crest_shows_the_official_class_icon():
    # owner request 2026-10-06: the page crest uses wowforevertalent.com's class icon (class_<name>);
    # the drawn SVG crest remains the fallback when the icon isn't cached
    html = render([MAGE, ROGUE], {"class_rogue": bytes([0xFF, 0xD8])})
    assert "ICONS['class_'+CLASS]" in html and 'class="crest-icon"' in html
    assert '"class_rogue": "data:image/jpeg;base64,' in html
