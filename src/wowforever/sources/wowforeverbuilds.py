"""wowforeverbuilds.com (#460): community spec guides, one PvE and one PvP guide per spec, each carrying its build as a
talent-calculator link. Only facts are kept (decoded build, link, title, date), credited; never the guide text.

robots.txt allows everything but /api/, /auth/ and /account. No license is stated.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from wowforever.rules import check_build
from wowforever.schema import ClassData
from wowforever.sources.wowforevertalent import decode_astro

BASE_URL = "https://wowforeverbuilds.com"


@dataclass(frozen=True)
class Calculator:
    class_slug: str
    build: str                                        # the game build its talent data is from
    tree_names: tuple[str, ...]
    trees: tuple[tuple[tuple[str, int], ...], ...]    # per tree, (talent name, max rank) in build-code order
    positions: tuple[tuple[tuple[int, int], ...], ...]  # per tree, each talent's (row, col) in the same order


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


@dataclass(frozen=True)
class Snapshot:
    date: str                                         # YYYY-MM-DD the site was saved
    calculators: Mapping[str, Calculator]             # by class slug
    guides: Mapping[str, GuideBuild]                  # by guide slug


def parse_calculator(page_html: str) -> Calculator:
    """A class's talent calculator page (`/talents/<class>`): its talents in build-code order and its game build."""
    island = re.search(r'component-url="/_astro/TalentCalculator[^"]*"[^>]*props="([^"]+)"', page_html)
    build = re.search(r"build\s*(1\.60\.\d+\.\d+)", page_html)
    if island is None or build is None:
        raise ValueError("not a wowforeverbuilds.com talent calculator page")
    cls = decode_astro(json.loads(html.unescape(island.group(1)))["cls"])
    trees = tuple(tuple((t["name"], int(t["maxRank"])) for t in tree["talents"]) for tree in cls["trees"])
    positions = tuple(tuple((int(t["row"]), int(t["col"])) for t in tree["talents"]) for tree in cls["trees"])
    return Calculator(cls["slug"], build.group(1), tuple(tree["name"] for tree in cls["trees"]), trees, positions)


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


def _tree(calc: Calculator, index: int) -> tuple[tuple[str, int, int, int], ...]:
    """Tree `index` of a calculator in build-code order: (name, max rank, row, col) per talent."""
    return tuple((name, rank, *pos) for (name, rank), pos in zip(calc.trees[index], calc.positions[index]))


def standard_build(slug: str, history: Sequence[Snapshot], cls: ClassData) -> tuple[dict[str, int] | None, str]:
    """The build a guide stands for on our trees, or (None, why not).

    `history` is every saved snapshot of the site, oldest first; the last is current. A code's digits follow the
    calculator in place when the code was last changed, so a code that outlived a calculator change is read with the
    old calculator. A code that changed in the same gap as its calculator is dropped unless the old calculator can't
    read it. The trees the build spends points in must match ours exactly, and the build must be legal.
    """
    latest = history[-1]
    guide = latest.guides.get(slug)
    if guide is None:
        return None, f"{slug}: not in the {latest.date} snapshot"
    first = len(history) - 1
    while first > 0:
        earlier = history[first - 1].guides.get(slug)
        if earlier is None or earlier.code != guide.code:
            break
        first -= 1
    calc = history[first].calculators[guide.class_slug]
    try:
        ranks = decode(guide.code, calc)
    except ValueError as e:
        return None, f"{slug}: {e}"
    used = [i for i, part in enumerate(guide.code.split("-")) if part.strip("0")]
    if first > 0:
        before = history[first - 1].calculators[guide.class_slug]
        if any(_tree(before, i) != _tree(calc, i) for i in used):
            try:
                decode(guide.code, before)
            except ValueError:
                pass
            else:
                return None, (f"{slug}: the build and the calculator both changed between {history[first - 1].date} "
                              f"and {history[first].date}; can't tell which trees it was made on")
    trees = {tree.name: tree for tree in cls.trees}
    build: dict[int, int] = {}
    for i in used:
        label = calc.tree_names[i]
        tree = trees.get(label)
        talents = {cls.talent(tid).name: cls.talent(tid) for tid in tree.talent_ids} if tree else {}
        if set(_tree(calc, i)) != {(t.name, t.max_rank, t.row, t.col) for t in talents.values()}:
            return None, (f"{slug}: {label}: the build was made on the {calc.build} calculator "
                          f"({history[first].date}), whose tree differs from ours")
        for name, _ in calc.trees[i]:
            if name in ranks:
                build[talents[name].talent_id] = ranks[name]
    errors = check_build(cls, build, cls.rules.max_level)
    if errors:
        return None, f"{slug}: not legal: " + "; ".join(errors)
    return ranks, ""
