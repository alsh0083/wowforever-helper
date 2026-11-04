"""wowforevertalents.com (#458): per-talent pages with every rank's text, on the client build plus server hotfixes.

robots.txt allows everything but /api/; only the HTML pages are read. No license is stated (owner decision 2026-10-31:
use it and credit it).
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wowforever.sources.wowforevertalent import WftPage

BASE_URL = "https://wowforevertalents.com"


@dataclass(frozen=True)
class TalentPage:
    name: str
    class_name: str
    tree: str
    max_rank: int
    ranks: tuple[str, ...]
    sources: tuple[str, ...]


def _text(fragment: str) -> str:
    """Tags dropped, entities decoded, whitespace collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def talent_url(class_slug: str, slug: str) -> str:
    return f"{BASE_URL}/{class_slug}/talents/{slug}/"


def talent_slugs(class_html: str, class_slug: str) -> list[str]:
    """Each talent page linked from a class page, once, in page order."""
    found = re.findall(rf'href="/{re.escape(class_slug)}/talents/([a-z0-9-]+)/"', class_html)
    return list(dict.fromkeys(found))


def parse_talent(page_html: str) -> TalentPage:
    """One talent page: its name, class, tree, rank count, the Forever text of every rank and its source lines."""
    heading = re.search(r"<h1[^>]*>(.*?)</h1>", page_html, re.S)
    where = re.search(r'<p class="tp-where"[^>]*>(.*?)</p>', page_html, re.S)
    ranks_list = re.search(r'<ol class="tp-ranks"[^>]*>(.*?)</ol>', page_html, re.S)
    if heading is None or where is None or ranks_list is None:
        raise ValueError("not a wowforevertalents.com talent page")
    name = _text(heading.group(1))
    links = [_text(a) for a in re.findall(r"<a[^>]*>(.*?)</a>", where.group(1), re.S)]
    count = re.search(r"(\d+) ranks?\b", _text(where.group(1)))
    if len(links) < 2 or count is None:
        raise ValueError(f"{name}: no class, tree or rank count")
    ranks = tuple(_text(t) for t in re.findall(r'<span class="tp-rank-t"[^>]*>(.*?)</span>', ranks_list.group(1), re.S))
    max_rank = int(count.group(1))
    if len(ranks) != max_rank:
        raise ValueError(f"{name}: {len(ranks)} rank texts for {max_rank} ranks")
    origin = re.search(r"Where this came from.*?<ul[^>]*>(.*?)</ul>", page_html, re.S)
    sources = tuple(_text(li) for li in re.findall(r"<li[^>]*>(.*?)</li>", origin.group(1), re.S)) if origin else ()
    return TalentPage(name, links[0], links[1], max_rank, ranks, sources)


TREE_NAMES = {"Shadow Magic": "Shadow", "Elemental Combat": "Elemental"}   # the site's Classic names -> our layouts


def class_trees(class_html: str) -> list[dict[str, Any]]:
    """The calculator grid on a class page: per tree its name and talents (name, row, col, maxRank, icon, classic)."""
    trees = []
    for article in re.findall(r'<article class="tree"[^>]*>(.*?)</article>', class_html, re.S):
        name = _text(re.search(r"<h2[^>]*>(.*?)</h2>", article, re.S).group(1))
        talents = []
        for cell in re.split(r'(?=<div class="node" )', article)[1:]:
            where = re.search(r'grid-row:(\d+);grid-column:(\d+)', cell)
            label = re.search(r'aria-label="([^"]+), rank \d+ of (\d+)', cell)
            icon = re.search(r'/icons/large/([^."/]+)\.jpg', cell)
            flag = re.search(r'<span class="flag (new|changed)"', cell)
            talents.append({
                "name": html.unescape(label.group(1)), "row": int(where.group(1)), "col": int(where.group(2)),
                "maxRank": int(label.group(2)), "icon": icon.group(1) if icon else "",
                "classic": {"status": flag.group(1) if flag else "same"},
            })
        trees.append({"name": TREE_NAMES.get(name, name), "talents": talents})
    return trees


def as_page(class_slug: str, class_html: str, talents: dict[str, TalentPage], *, game_build: str,
            data_version: str) -> WftPage:
    """The class page's grid with every talent's rank text, in the shape normalize and crosscheck read."""
    trees = class_trees(class_html)
    for tree in trees:
        for talent in tree["talents"]:
            found = talents.get(talent["name"])
            if found is None:
                raise ValueError(f"no talent page for {talent['name']}")
            if found.max_rank != talent["maxRank"]:
                raise ValueError(f"{talent['name']}: the grid has {talent['maxRank']} ranks, its page {found.max_rank}")
            talent["ranks"] = [{"rank": i, "text": text} for i, text in enumerate(found.ranks, start=1)]
    return WftPage(class_id=class_slug, game_build=game_build, page_data_version=f"wowforevertalents-{data_version}",
                   props_version="", trees=trees, popular=None)


CLIENT_BUILD = re.compile(r"Forever client build (1\.60\.\d+\.\d+)")


def fetch(class_slug: str, *, http_get: Callable[[str], str], raw_dir: Path, delay: float = 1.5,
          sleep: Callable[[float], None] = time.sleep) -> tuple[Path, WftPage]:
    """A class page and every talent page it links, saved under `raw_dir/<class>/` (immutable: a saved snapshot is
    read back instead of fetched again), as the page normalize reads. `raw_dir`'s name is the data version."""
    folder = raw_dir / class_slug
    class_path = folder / "class.html"
    if not class_path.exists():
        class_html = http_get(f"{BASE_URL}/{class_slug}/")
        pages = {}
        for slug in talent_slugs(class_html, class_slug):
            sleep(delay)
            pages[slug] = http_get(talent_url(class_slug, slug))
        (folder / "talents").mkdir(parents=True, exist_ok=True)
        for slug, text in pages.items():
            (folder / "talents" / f"{slug}.html").write_text(text, encoding="utf-8", newline="")
        class_path.write_text(class_html, encoding="utf-8", newline="")
    class_html = class_path.read_text(encoding="utf-8")
    talents = {}
    builds = []
    for slug in talent_slugs(class_html, class_slug):
        talent = parse_talent((folder / "talents" / f"{slug}.html").read_text(encoding="utf-8"))
        talents[talent.name] = talent
        builds += [m.group(1) for line in talent.sources for m in [CLIENT_BUILD.search(line)] if m]
    if not builds:
        raise ValueError(f"{class_slug}: no client build on any talent page")
    game_build = max(set(builds), key=builds.count)
    result = as_page(class_slug, class_html, talents, game_build=game_build, data_version=raw_dir.name)
    files = sorted(folder.rglob("*.html"))
    digest = hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest()
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps({
            "source": "wowforevertalents.com", "url": f"{BASE_URL}/{class_slug}/", "game_build": game_build,
            "pages": len(files), "sha256": digest,
        }, indent=1), encoding="utf-8", newline="\n")
    return manifest_path, result
