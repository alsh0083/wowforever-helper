"""wowforeverbuilds.com (#460): community spec guides, one PvE and one PvP guide per spec, each carrying its build as a
talent-calculator link. Only facts are kept (decoded build, link, title, date), credited; never the guide text.

robots.txt allows everything but /api/, /auth/ and /account. No license is stated.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass

from wowforever.sources.wowforevertalent import decode_astro

BASE_URL = "https://wowforeverbuilds.com"


@dataclass(frozen=True)
class Calculator:
    class_slug: str
    build: str                                        # the game build its talent data is from
    tree_names: tuple[str, ...]
    trees: tuple[tuple[tuple[str, int], ...], ...]    # per tree, (talent name, max rank) in build-code order


@dataclass(frozen=True)
class GuideBuild:
    slug: str
    class_slug: str
    code: str
    modified: str                                     # YYYY-MM-DD
    title: str

    @property
    def url(self) -> str:
        return f"{BASE_URL}/guide/{self.slug}"


def parse_calculator(page_html: str) -> Calculator:
    """A class's talent calculator page (`/talents/<class>`): its talents in build-code order and its game build."""
    island = re.search(r'component-url="/_astro/TalentCalculator[^"]*"[^>]*props="([^"]+)"', page_html)
    build = re.search(r"build\s*(1\.60\.\d+\.\d+)", page_html)
    if island is None or build is None:
        raise ValueError("not a wowforeverbuilds.com talent calculator page")
    cls = decode_astro(json.loads(html.unescape(island.group(1)))["cls"])
    trees = tuple(tuple((t["name"], int(t["maxRank"])) for t in tree["talents"]) for tree in cls["trees"])
    return Calculator(cls["slug"], build.group(1), tuple(tree["name"] for tree in cls["trees"]), trees)


def decode(code: str, calc: Calculator) -> dict[str, int]:
    """A `?b=` build code: one digit per talent in calculator order, trees split by "-", trailing zeros left out.
    Returns the talents with points."""
    parts = code.split("-")
    if len(parts) > len(calc.trees):
        raise ValueError(f"{len(parts)} trees in {code!r}; the calculator has {len(calc.trees)}")
    ranks: dict[str, int] = {}
    for digits, label, tree in zip(parts, calc.tree_names, calc.trees):
        if len(digits) > len(tree):
            raise ValueError(f"{label}: {len(digits)} digits for {len(tree)} talents")
        for digit, (name, max_rank) in zip(digits, tree):
            if not digit.isdigit():
                raise ValueError(f"{digit!r} in {code!r} is not a digit")
            if int(digit) > max_rank:
                raise ValueError(f"{label}/{name}: rank {digit} of {max_rank}")
            if int(digit):
                ranks[name] = int(digit)
    return ranks


def parse_guide(page_html: str, slug: str) -> GuideBuild:
    """A spec guide: its first talent-calculator link, title and last-modified date."""
    link = re.search(r'href="/talents/([a-z-]+)\?b=([0-9-]+)', page_html)
    title = re.search(r"<h1[^>]*>(.*?)</h1>", page_html, re.S)
    modified = re.search(r'"dateModified":"(\d{4}-\d{2}-\d{2})', page_html)
    if link is None or title is None or modified is None:
        raise ValueError(f"{slug}: no build link, title or date")
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", title.group(1)))).strip()
    return GuideBuild(slug, link.group(1), link.group(2), modified.group(1), text)


def guide_slugs(listing_html: str) -> list[str]:
    """The PvE and PvP spec guides a class's guide listing links, sorted, once each."""
    return sorted(set(re.findall(r'href="/guide/([a-z0-9-]+-(?:pve|pvp)-guide)"', listing_html)))
