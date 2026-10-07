"""Icy Veins' WoW Forever spec guides: their level-30 talent builds, as point-by-point orders, used as a
background sanity check on the first points of each talent path (owner request, 2026-10-07).

Each guide embeds its builds as read-only talent calculators whose `#tc-...` code is one character per
point, in the order taken. A character indexes the class's talents in tree order, skipping the empty
grid cells of Icy Veins' talent JSON (`static.icy-veins.com/json/forever-talent-calculator/<class>.json`),
through the alphabet 0-9a-zA-Z. Only those facts are kept (build title, level, order, guide link and
date), never guide text; Icy Veins is credited where the builds are shown.

Fetching happens only on demand (`wowforever icy-veins --refresh`), a couple of seconds apart: about 28
requests. robots.txt allows the site and its terms don't restrict automated reading (checked
2026-10-07). Raw pages are cached in data/cache/icy-veins/ (gitignored).
"""

from __future__ import annotations

import html
import json
import re
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

SITE = "https://www.icy-veins.com"
HUB = f"{SITE}/wow-forever/"
CALC_JSON = "https://static.icy-veins.com/json/forever-talent-calculator/{}.json"
CLASSES = ("druid", "hunter", "mage", "paladin", "priest", "rogue", "shaman", "warlock", "warrior")
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
GUIDE = re.compile(r'href="/wow-forever/([a-z-]+-(?:' + "|".join(CLASSES) + r')-[a-z-]*guide)"')


def guide_slugs(hub: str) -> list[str]:
    """The spec guide slugs linked from the Forever hub (e.g. shadow-priest-ranged-dps-pve-guide)."""
    return sorted(set(GUIDE.findall(hub)))


def guide_class(slug: str) -> str:
    return next(c for c in CLASSES if f"-{c}-" in f"-{slug}-")


def fetch(cache_dir: Path, http_get: Callable[[str], str], *, delay: float = 2.0) -> None:
    """Save the hub, every spec guide and each class's talent JSON into `cache_dir` (on demand only)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    hub = http_get(HUB)
    (cache_dir / "hub.html").write_text(hub, encoding="utf-8", newline="\n")
    for slug in guide_slugs(hub):
        time.sleep(delay)
        (cache_dir / f"{slug}.html").write_text(http_get(f"{SITE}/wow-forever/{slug}"), encoding="utf-8", newline="\n")
    for c in CLASSES:
        time.sleep(delay)
        (cache_dir / f"talents-{c}.json").write_text(http_get(CALC_JSON.format(c)), encoding="utf-8", newline="\n")


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def parse_guide(page: str) -> dict[str, Any]:
    """The guide's last-updated date and each embedded build: the heading above it and its code."""
    updated = re.search(r"Last Updated:\s*([A-Z][a-z]{2} \d{1,2}, \d{4})", _text(page))
    builds = []
    for m in re.finditer(r'data-talentcalculator-pointsurl="#tc-([0-9A-Za-z]*)"', page):
        heads = list(re.finditer(r'<h([23])[^>]*id="([^"]+)"[^>]*>(.*?)</h\1>', page[:m.start()], re.S))
        h3 = next((h for h in reversed(heads) if h.group(1) == "3"), None)
        h2 = next((h for h in reversed(heads) if h.group(1) == "2"), None)
        section = _text(h2.group(3)) if h2 else ""
        level = re.search(r"Level (\d+)", section)
        builds.append({"code": m.group(1), "title": _text(h3.group(3)) if h3 and (not h2 or h3.start() > h2.start()) else section,
                       "anchor": (h3 or h2).group(2) if (h3 or h2) else "", "level": int(level.group(1)) if level else None})
    return {"updated": updated.group(1) if updated else None, "builds": builds}


def talent_list(calculator: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(tree, talent name) for each talent in code order: trees in order, grid cells in order, empty skipped."""
    return [(group["name"], t["name"]) for group in calculator["talentGroups"] for t in group["talents"] if t]


def decode(code: str, calculator: Mapping[str, Any]) -> list[str]:
    """Talent names, one per point in the order taken."""
    talents = talent_list(calculator)
    return [talents[ALPHABET.index(ch)][1] for ch in code]


def compare(dataset: Mapping[str, Any], reports: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """For every build in `reports`, how many of the matching guide build's points (same class and main
    tree) its talent path shares by the same point count: a sanity check on the first points only,
    since the guide builds stop at level 30 and talent paths spend only the final build's talents."""
    from collections import Counter

    rows = []
    for report in reports:
        cls = report.get("class", "mage")
        tree = {t["name"]: t["tree"] for t in report["talents"].values()}

        def main(order: list[str]) -> str:
            return Counter(tree.get(n) for n in order).most_common(1)[0][0]

        guides = [g for g in dataset["builds"] if g["class"] == cls and all(n in tree for n in g["order"])]
        for b in report["builds"]:
            ours = [report["talents"][str(t)]["name"] for t in b["order"]]
            for g in [g for g in guides if main(g["order"]) == main(ours)][:1]:
                n = len(g["order"])
                mine, theirs = Counter(ours[:n]), Counter(g["order"])
                rows.append({"class": cls, "build": b["id"], "guide": g["guide"], "title": g["title"], "points": n,
                             "shared": sum(min(theirs[k], mine[k]) for k in theirs)})
    return rows


def markdown(rows: list[dict[str, Any]]) -> str:
    lines = ["| Class | Build | Shared with Icy Veins | Guide build |", "|---|---|---|---|"]
    lines += [f"| {r['class'].title()} | {r['build']} | {r['shared']} of {r['points']} | {r['guide']}: {r['title']} |"
              for r in sorted(rows, key=lambda r: (r["class"], -r["shared"]))]
    return "\n".join(lines)


def build_dataset(cache_dir: Path, *, checked_at: str) -> dict[str, Any]:
    """Every decoded guide build, with its guide link and date."""
    out = []
    for path in sorted(cache_dir.glob("*-guide.html")):
        slug = path.stem
        cls = guide_class(slug)
        calc = json.loads((cache_dir / f"talents-{cls}.json").read_text(encoding="utf-8"))
        guide = parse_guide(path.read_text(encoding="utf-8"))
        for b in guide["builds"]:
            if not b["code"]:
                continue
            out.append({"class": cls, "guide": slug, "url": f"{SITE}/wow-forever/{slug}#{b['anchor']}",
                        "title": b["title"], "level": b["level"], "updated": guide["updated"],
                        "order": decode(b["code"], calc)})
    return {"source": "Icy Veins WoW Forever guides", "checked_at": checked_at, "builds": out}
