"""wow-forever.gg talent pick rates, a comparison source only (#450).

Fixture saved 2026-10-29 (tests/fixtures/wowforevergg/README.md): the page's `trait-data` JSON has `rates`
(talent node id -> % of finished builds that take it), `ratesBuilds` and the trees' nodes (id -> name).
"""

from pathlib import Path

import pytest

from wowforever.sources.wowforevergg import pick_rates, unusual_picks

PAGE = (Path(__file__).resolve().parent / "fixtures" / "wowforevergg" / "mage-20261029.html").read_text(
    encoding="utf-8")


def test_pick_rates_by_talent_name():
    data = pick_rates(PAGE)
    # "Game data from build <strong>1.60.1.70532</strong>"; "... 13 Sept 2026 to 22 Oct 2026"; ratesBuilds 287
    assert data["game_build"] == "1.60.1.70532"
    assert data["window"] == "13 Sept 2026 to 22 Oct 2026"
    assert data["builds"] == 287
    rates = data["rates"]
    assert len(rates) == 54
    assert rates["Missile Barrage"] == pytest.approx(58.1)
    assert rates["Ice Lance"] == pytest.approx(64.2)
    assert rates["Improved Fire Ward"] == pytest.approx(2.8)
    assert rates["Piercing Ice"] == pytest.approx(53.8)     # still in its 70532 trees


def test_unusual_picks_flags_rare_talents_taken_and_common_ones_skipped():
    rates = {"Ice Lance": 64.2, "Missile Barrage": 58.1, "Improved Fire Ward": 2.8, "Frost Warding": 8.0,
             "Arcane Shielding": 16.5}
    final = {"Improved Fire Ward": 2, "Arcane Shielding": 1, "Missile Barrage": 2, "Brand New Talent": 1}
    rare, skipped = unusual_picks(final, rates)
    # taken under 15%: Improved Fire Ward (2.8); Arcane Shielding 16.5 is not under 15; unknown names are ignored
    assert rare == [("Improved Fire Ward", 2.8)]
    # skipped at 60% or more: Ice Lance (64.2); Missile Barrage 58.1 is under 60
    assert skipped == [("Ice Lance", 64.2)]


def test_unusual_picks_thresholds_and_order():
    rates = {"A": 1.0, "B": 14.9, "C": 15.0, "D": 60.0, "E": 90.0}
    rare, skipped = unusual_picks({"A": 1, "B": 1, "C": 1}, rates, low=15.0, high=60.0)
    assert rare == [("A", 1.0), ("B", 14.9)]           # ascending rate, strictly under `low`
    assert skipped == [("E", 90.0), ("D", 60.0)]       # descending rate, at or above `high`
