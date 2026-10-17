"""Post-patch community builds stay provisional until the meta settles (#369 follow-up, owner 2026-10-16:
"check again frequently to see what has leveled out")."""

import tomllib
from pathlib import Path

from wowforever.builds import Build

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "config" / "builds" / "shaman-elemental.toml").read_text(encoding="utf-8")
ENTRY = {"rank": 5, "saved": 92, "points": [37, 13, 0],
         "final": {"Convection": 5, "Concussion": 5, "Call of Flame": 3}, "overlap": 13}


def test_signature_ignores_order_and_zero_ranks():
    from wowforever.community import final_signature

    assert final_signature({"A": 1, "B": 2}) == final_signature({"B": 2, "A": 1, "C": 0})
    assert final_signature({"A": 1}) != final_signature({"A": 2})


def test_a_thin_sample_is_marked_provisional():
    from wowforever.community import PROVISIONAL_SAVES, final_signature, refreshed_toml

    assert PROVISIONAL_SAVES == 20
    raw = tomllib.loads(refreshed_toml(TEXT, dict(ENTRY, saved=5), window="w", today="2026-10-16"))
    assert raw["provisional"] == "5 saves, 2026-10-16"
    assert raw["refreshed"] == f"5:{final_signature(ENTRY['final'])}"
    raw = tomllib.loads(refreshed_toml(TEXT, ENTRY, window="w", today="2026-10-16"))
    assert "provisional" not in raw and raw["refreshed"].startswith("5:")


def _build(**more):
    return Build("x", "X", "", {"Convection": 5, "Concussion": 5, "Call of Flame": 3}, class_name="shaman",
                 origin="community", **more)


def test_refresh_status():
    from wowforever.community import final_signature, refresh_status

    sig = final_signature(ENTRY["final"])
    # same player build as last time: stable; with enough saves the provisional mark goes
    assert refresh_status(_build(provisional="5 saves, d", refreshed=f"5:{sig}"), dict(ENTRY, saved=8)) == "stable"
    assert refresh_status(_build(provisional="5 saves, d", refreshed=f"5:{sig}"), ENTRY) == "settled"
    # the closest player build changed since: moved
    assert refresh_status(_build(provisional="5 saves, d", refreshed="5:other"), ENTRY) == "moved"
    # never refreshed (hand-adjusted): moved onto player data
    assert refresh_status(_build(adjusted="1.60.1.70425: x"), ENTRY) == "moved"


def test_dashboard_caption_names_a_provisional_build():
    from wowforever.dashboard import standard_caption

    assert standard_caption({"origin": "community", "provisional": "5 saves, 2026-10-16"}) == \
        "Community standard (provisional, 5 saves)"


def test_builds_load_the_marks():
    b = Build.load(ROOT / "config" / "builds" / "priest-shadow.toml")
    assert b.provisional.startswith("5 saves") and b.refreshed.startswith("2:")
