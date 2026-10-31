"""wowforevertalents.com (#458): per-talent pages with every rank's text, on the client build plus server hotfixes.

robots.txt allows everything but /api/; only the HTML pages are read. No license is stated (owner decision 2026-10-31:
use it and credit it).
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

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
