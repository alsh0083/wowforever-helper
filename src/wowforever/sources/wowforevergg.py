"""Reader for wow-forever.gg class talent pages (pick rates).

Each class page embeds its pick-rate data in a <script type="application/json"
id="trait-data"> block: `rates` maps node id (string) to the percent of finished builds
that pick the node, `ratesBuilds` counts the finished builds aggregated, and `trees`
provides the int id to talent name mapping. The page also shows the game build
("Game data from build <strong>...</strong>") and the aggregation window
(class="calc-rates-count", e.g. "13 Sept 2026 to 22 Oct 2026").

The site states no license, so its numbers are for comparison only (flagging a build's
unusual picks against them); they are never shown on the dashboard (#450).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

SOURCE = "wow-forever.gg"

_TRAIT_DATA = re.compile(
    r'<script type="application/json" id="trait-data">(.*?)</script>', re.S
)
_GAME_BUILD = re.compile(r"Game data from build <strong>([^<]+)</strong>")
_RATES_WINDOW = re.compile(
    r'class="calc-rates-count">.*?(\d+ \w+ \d{4} to \d+ \w+ \d{4})', re.S
)


def pick_rates(page_html: str) -> dict[str, Any]:
    """Extract game build, window, build count, and per-talent pick rates."""
    payload = json.loads(_TRAIT_DATA.search(page_html).group(1))
    id_to_name = {
        node["id"]: node["name"] for tree in payload["trees"] for node in tree["nodes"]
    }
    rates = {
        id_to_name[int(node_id)]: percent for node_id, percent in payload["rates"].items()
    }
    return {
        "game_build": _GAME_BUILD.search(page_html).group(1),
        "window": _RATES_WINDOW.search(page_html).group(1),
        "builds": payload["ratesBuilds"],
        "rates": rates,
    }


def unusual_picks(
    final: Mapping[str, int],
    rates: Mapping[str, float],
    *,
    low: float = 15.0,
    high: float = 60.0,
) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    """Compare a build's picks to pick rates.

    Returns (rare, skipped): picks present in the build with rate strictly under `low`,
    and talents with rate at or above `high` the build does not take (missing or 0).
    Each list holds (name, rate) tuples; rare is sorted by rate ascending, skipped by
    rate descending. Names missing from `rates` are ignored.
    """
    rare = sorted(
        (
            (name, rates[name])
            for name, rank in final.items()
            if rank > 0 and name in rates and rates[name] < low
        ),
        key=lambda item: item[1],
    )
    skipped = sorted(
        (
            (name, rate)
            for name, rate in rates.items()
            if rate >= high and final.get(name, 0) == 0
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    return rare, skipped
