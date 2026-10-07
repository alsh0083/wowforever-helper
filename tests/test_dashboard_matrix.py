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
    assert "Yours" not in HTML                   # owner request, 2026-10-07: no tag on hand-made builds
    assert re.search(r'class="score-num" title="Model score as a share[^"]*">100%<', HTML)
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


def test_best_pair_takes_the_top_build_of_each_column():
    from wowforever.dashboard import best_pair
    scores = {}
    for s in PAYLOAD["shortlist"]:
        cands = s["candidates"] if isinstance(s["candidates"], dict) else {}
        for bid, score in cands.items():
            scores[(s["focus"], bid)] = score
    pvp, pve = best_pair(PAYLOAD)
    assert pvp == max((sc, b) for (f, b), sc in scores.items() if f == "PvP")[::-1]
    assert pve == max((sc, b) for (f, b), sc in scores.items() if f == "PvE")[::-1]
    assert "Highest-scoring pair" in HTML


def test_pair_divergence_is_described():
    assert "Orders match until level" in HTML     # pair mates show where their orders split
    assert "within one cell only" not in HTML      # scores compare across a whole column
