"""Dashboard spec matrix (#28 view), pairs (#41) and save-change warnings (#30).
Structure checks on the rendered HTML; behaviour is reviewed by Claude in a browser."""

import json
import re
from pathlib import Path

from wowforever.dashboard import render

PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "dashboard" / "payload.json").read_text(encoding="utf-8"))
HTML = render(PAYLOAD, {})


def test_matrix_has_a_cell_per_slot_in_payload_order():
    cells = re.findall(r'data-slot="([^"]+)"', HTML)
    assert cells == [f'{s["archetype"]}|{s["focus"]}' for s in PAYLOAD["shortlist"]]


def test_standards_owner_builds_and_model_picks_are_labelled():
    assert "Model pick, unproven" in HTML
    assert "Community standard" in HTML
    assert "Yours" in HTML                       # hand-written builds that qualify
    assert "No community standard yet" in HTML   # empty standard slots say so


def test_hybrid_rows_blend_their_two_schools():
    # Fire/Frost row label uses both school colours
    assert re.search(r'data-archetype="Fire/Frost"[^>]*style="[^"]*--from:var\(--frost\)[^"]*--to:var\(--fire\)', HTML)


def test_pairs_and_save_versioning_are_present():
    assert "Pairs with" in HTML
    assert "wow-forever-save-v5" in HTML          # saves record talent + rank per checked level
    assert "carried over" in HTML                 # the patch-change notice wording


def test_no_all_caps_eyebrows_in_new_sections():
    matrix = HTML[HTML.index('id="spec-matrix"'):HTML.index('id="spec-matrix"') + 4000]
    assert "text-transform:uppercase" not in matrix.replace(" ", "")
