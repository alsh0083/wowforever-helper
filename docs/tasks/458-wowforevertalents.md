# Task #458 (part 1): read wowforevertalents.com talent pages

Make `tests/test_wowforevertalents.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Create exactly one file: `src/wowforever/sources/wowforevertalents.py`. Edit no other file. Make no network requests.
- Before you start, `tests/test_wowforevertalents.py` fails at import: the module doesn't exist yet. Nothing else should fail.
- Run `.venv/Scripts/python -m pytest tests/test_wowforevertalents.py -q` after each step, then the fast suite once at the end.

## Why
wowforevertalent.com (singular), our rank-text source, is stuck on build 70425. wowforevertalents.com (plural) has
build 70707 plus the server hotfixes, with one page per talent listing every rank's text. Each page has an `<h1>` name,
a `<p class="tp-where">` with class and tree links and "N ranks", an `<ol class="tp-ranks">` with one
`<span class="tp-rank-t">` per rank (a second `<ol class="tp-ranks tp-ranks-classic">` holds the Classic Era wording and
must be ignored), and a "Where this came from" list.

## Step 1: create the file with the header, `TalentPage` and `_text`
```python
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
```

## Step 2: add `talent_url` and `talent_slugs` at the end of the file
```python
def talent_url(class_slug: str, slug: str) -> str:
    return f"{BASE_URL}/{class_slug}/talents/{slug}/"


def talent_slugs(class_html: str, class_slug: str) -> list[str]:
    """Each talent page linked from a class page, once, in page order."""
    found = re.findall(rf'href="/{re.escape(class_slug)}/talents/([a-z0-9-]+)/"', class_html)
    return list(dict.fromkeys(found))
```

## Step 3: add `parse_talent` at the end of the file
```python
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
```

## Done when
- `tests/test_wowforevertalents.py` passes (7 tests); the fast suite has no other new failures.
- Only `src/wowforever/sources/wowforevertalents.py` is new; no other file changed.
