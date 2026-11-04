"""wowforeverbuilds.com (#460): community spec guides, one PvE and one PvP guide per spec, each carrying its build as a
talent-calculator link. Only facts are kept (decoded build, link, title, date), credited; never the guide text.

robots.txt allows everything but /api/, /auth/ and /account. No license is stated.
"""

from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from wowforever.rules import check_build
from wowforever.schema import ClassData
from wowforever.sources.wowforevertalent import decode_astro

BASE_URL = "https://wowforeverbuilds.com"
CLASSES = ("druid", "hunter", "mage", "paladin", "priest", "rogue", "shaman", "warlock", "warrior")
ROW_POINTS = 5                                        # points spent in a tree's earlier rows per row


@dataclass(frozen=True)
class Calculator:
    class_slug: str
    build: str                                        # the game build its talent data is from
    tree_names: tuple[str, ...]
    trees: tuple[tuple[tuple[str, int], ...], ...]    # per tree, (talent name, max rank) in build-code order
    positions: tuple[tuple[tuple[int, int], ...], ...]  # per tree, each talent's (row, col) in the same order
    requires: tuple[tuple[tuple[int, int] | None, ...], ...]  # per tree, (index in the tree, rank) each talent needs
    texts: tuple[tuple[tuple[str, ...], ...], ...] = ()  # per tree, each talent's rank text (#463); () when unknown


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
    requires = tuple(_requires(tree["talents"]) for tree in cls["trees"])
    texts = tuple(tuple(tuple(r["description"] for r in t["ranks"]) for t in tree["talents"]) for tree in cls["trees"])
    return Calculator(cls["slug"], build.group(1), tuple(tree["name"] for tree in cls["trees"]), trees, positions,
                      requires, texts)


def _requires(talents: list[dict]) -> tuple[tuple[int, int] | None, ...]:
    """Each talent's prerequisite as (index of the required talent in the same tree, rank), or None."""
    index = {t["id"]: i for i, t in enumerate(talents)}
    out: list[tuple[int, int] | None] = []
    for t in talents:
        needs = t.get("requires") or []
        if len(needs) > 1 or any(n["id"] not in index for n in needs):
            raise ValueError(f"{t['name']}: unsupported prerequisite {needs!r}")
        out.append((index[needs[0]["id"]], int(needs[0]["ranks"])) if needs else None)
    return tuple(out)


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


def calculator_errors(ranks: Mapping[str, int], calc: Calculator) -> list[str]:
    """What breaks a decoded build on the calculator's own trees: 5 points per row above, and prerequisites."""
    errors: list[str] = []
    for label, tree, pos, needs in zip(calc.tree_names, calc.trees, calc.positions, calc.requires):
        points = [ranks.get(name, 0) for name, _ in tree]
        for (name, _), (row, _), need, taken in zip(tree, pos, needs, points):
            if not taken:
                continue
            spent = sum(p for p, (r, _) in zip(points, pos) if r < row)
            if spent < ROW_POINTS * row:
                errors.append(f"{label}/{name}: needs {ROW_POINTS * row} points in earlier rows, has {spent}")
            if need is not None and points[need[0]] < need[1]:
                errors.append(f"{label}/{name}: needs {tree[need[0]][0]} at rank {need[1]}")
    return errors


def title_misses(ranks: Mapping[str, int], title: str, names: Iterable[str]) -> list[str]:
    """Talents among `names` that a guide's title names but its build doesn't take, sorted. Longer names match
    first, so "Bite" inside "Primal Bite" isn't a mention of Bite."""
    named = []
    for name in sorted(set(names), key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(name) + r"(?!\w)"
        if re.search(pattern, title, re.IGNORECASE):
            named.append(name)
            title = re.sub(pattern, "|", title, flags=re.IGNORECASE)
    return sorted(name for name in named if name not in ranks)


def _changed(a: Calculator, b: Calculator, used: Sequence[int]) -> bool:
    return any(i >= len(a.trees) or i >= len(b.trees) or _tree(a, i) != _tree(b, i) for i in used)


_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _same_text(a: str, b: str) -> bool:
    """Rank text compared word for word, numbers within 1% (sites round computed values differently and write 3 or
    3.0); spacing and a final full stop don't count."""
    a, b = (" ".join(text.split()).rstrip(".") for text in (a, b))
    if _NUMBER.sub("#", a) != _NUMBER.sub("#", b):
        return False
    return all(abs(float(x) - float(y)) <= 0.01 * max(float(x), float(y))
               for x, y in zip(_NUMBER.findall(a), _NUMBER.findall(b)))


def standard_build(slug: str, history: Sequence[Snapshot], cls: ClassData) -> tuple[dict[str, int] | None, str]:
    """The build a guide stands for on our trees, or (None, why not).

    `history` is every saved snapshot of the site, oldest first; the last is current. A code's digits follow the
    calculator in place when the code was last changed, so a code that outlived a calculator change is read with the
    old calculator. When a code changed in the same gap as its calculator, each calculator reads it, and a reading
    counts only if it is legal on that calculator's trees and takes every talent the guide's title names; the guide
    is kept only when exactly one reading counts, or both count and agree. The trees the build spends points in must
    then match ours exactly, in layout and in every talent's rank text (a build picked for other numbers isn't a
    current standard, #463), and the build must be legal.
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
    made_on = history[first].date
    used = [i for i, part in enumerate(guide.code.split("-")) if part.strip("0")]
    before = history[first - 1].calculators[guide.class_slug] if first > 0 else None
    if before is not None and _changed(before, calc, used):
        names = [name for c in (before, calc) for tree in c.trees for name, _ in tree]
        readings = []
        for when, c in ((history[first - 1].date, before), (made_on, calc)):
            try:
                r = decode(guide.code, c)
            except ValueError:
                continue
            if not calculator_errors(r, c) and not title_misses(r, guide.title, names):
                readings.append((when, c, r))
        if len(readings) == 2 and readings[0][2] == readings[1][2]:
            readings = readings[1:]                   # both read the same talents: which one doesn't matter
        if len(readings) != 1:
            outcome = "two different plausible builds" if readings else "no plausible build"
            return None, (f"{slug}: the build and the calculator both changed between {history[first - 1].date} "
                          f"and {made_on}, and the two calculators read it as {outcome}")
        made_on, calc, ranks = readings[0]
    else:
        try:
            ranks = decode(guide.code, calc)
        except ValueError as e:
            return None, f"{slug}: {e}"
    trees = {tree.name: tree for tree in cls.trees}
    build: dict[int, int] = {}
    for i in used:
        label = calc.tree_names[i]
        tree = trees.get(label)
        talents = {cls.talent(tid).name: cls.talent(tid) for tid in tree.talent_ids} if tree else {}
        if set(_tree(calc, i)) != {(t.name, t.max_rank, t.row, t.col) for t in talents.values()}:
            return None, (f"{slug}: {label}: the build was made on the {calc.build} calculator "
                          f"({made_on}), whose tree differs from ours")
        changed = [name for (name, _), text in zip(calc.trees[i], calc.texts[i] if calc.texts else ())
                   if len(text) != len(talents[name].rank_text)
                   or not all(map(_same_text, text, talents[name].rank_text))]
        if changed:
            return None, (f"{slug}: {label}: the build was made on the {calc.build} calculator ({made_on}), "
                          f"whose rank text differs from ours for " + ", ".join(changed))
        for name, _ in calc.trees[i]:
            if name in ranks:
                build[talents[name].talent_id] = ranks[name]
    errors = check_build(cls, build, cls.rules.max_level)
    if errors:
        return None, f"{slug}: not legal: " + "; ".join(errors)
    return ranks, ""


def fetch(*, http_get: Callable[[str], str], raw_dir: Path, classes: Sequence[str] = CLASSES, delay: float = 1.5,
          sleep: Callable[[float], None] = time.sleep) -> Path:
    """Each class's calculator, guide listing and spec guides, saved gzipped under `raw_dir` (named YYYYMMDD). A
    saved snapshot is immutable: when its manifest exists nothing is fetched. Returns the manifest's path."""
    manifest_path = raw_dir / "manifest.json"
    if manifest_path.exists():
        return manifest_path
    pages: dict[str, str] = {}
    for n, class_slug in enumerate(classes):
        if n:
            sleep(delay)
        pages[f"talents-{class_slug}.html"] = http_get(f"{BASE_URL}/talents/{class_slug}")
        sleep(delay)
        listing = http_get(f"{BASE_URL}/guides/{class_slug}")
        pages[f"guides-{class_slug}.html"] = listing
        for slug in guide_slugs(listing):
            sleep(delay)
            pages[f"guide-{slug}.html"] = http_get(f"{BASE_URL}/guide/{slug}")
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, text in pages.items():
        (raw_dir / f"{name}.gz").write_bytes(gzip.compress(text.encode("utf-8"), mtime=0))
    manifest_path.write_text(json.dumps({
        "source": "wowforeverbuilds.com", "url": BASE_URL, "captured": _date(raw_dir.name),
        "classes": list(classes), "pages": len(pages), "sha256": _digest(raw_dir),
    }, indent=1), encoding="utf-8", newline="\n")
    return manifest_path


def _date(folder_name: str) -> str:
    return f"{folder_name[:4]}-{folder_name[4:6]}-{folder_name[6:]}"


def _read(path: Path) -> str:
    return gzip.decompress(path.read_bytes()).decode("utf-8")


def _digest(folder: Path) -> str:
    """sha256 of the pages as fetched (uncompressed), in file-name order."""
    pages = sorted(folder.glob("*.html.gz"))
    return hashlib.sha256(b"".join(gzip.decompress(p.read_bytes()) for p in pages)).hexdigest()


def load_snapshot(folder: Path) -> Snapshot:
    """A saved snapshot, checked against its manifest."""
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if _digest(folder) != manifest["sha256"]:
        raise ValueError(f"{folder}: pages changed since the snapshot was saved")
    calculators = {}
    for path in sorted(folder.glob("talents-*.html.gz")):
        calc = parse_calculator(_read(path))
        calculators[calc.class_slug] = calc
    guides = {}
    for path in sorted(folder.glob("guide-*.html.gz")):
        slug = path.name.removeprefix("guide-").removesuffix(".html.gz")
        guides[slug] = parse_guide(_read(path), slug)
    return Snapshot(manifest["captured"], calculators, guides)


def load_history(root: Path) -> list[Snapshot]:
    """Every saved snapshot under `root` (`data/raw/wowforeverbuilds/`), oldest first."""
    folders = [f for f in root.iterdir() if re.fullmatch(r"\d{8}", f.name) and (f / "manifest.json").exists()]
    return [load_snapshot(f) for f in sorted(folders, key=lambda f: f.name)]
