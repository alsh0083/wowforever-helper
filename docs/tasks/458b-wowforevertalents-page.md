# Task #458 (part 2): the class page's grid as the page normalize reads

Make `tests/test_wowforevertalents.py` pass (11 tests) without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/sources/wowforevertalents.py`. Make no network requests.
- Before you start, the test file fails at import (`as_page`, `class_trees` don't exist yet). Nothing else should fail.
- Run `.venv/Scripts/python -m pytest tests/test_wowforevertalents.py -q` after each step, then the fast suite once.

## Why
`normalize` and `crosscheck` read a calculator page (`WftPage` from `sources/wowforevertalent.py`): per tree its name
and talents with `name`, `row`, `col`, `maxRank`, `icon`, `classic.status` and `ranks` [{"rank", "text"}]. The class
page on wowforevertalents.com has that grid (`<article class="tree">` with an `<h2>` tree name, then
`<div class="node" style="grid-row:R;grid-column:C">` cells whose button `aria-label` reads "Name, rank 0 of N"), and the
talent pages have the rank text. Two tree names differ from our layouts ("Shadow Magic", "Elemental Combat").

## Step 1: imports
Replace the line `from dataclasses import dataclass` with:
```python
from dataclasses import dataclass
from typing import Any

from wowforever.sources.wowforevertalent import WftPage
```

## Step 2: add at the end of the file
```python
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
```

## Step 3: add at the end of the file
```python
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
```

## Done when
- `tests/test_wowforevertalents.py` passes (11 tests); the fast suite has no other new failures.
- Only `src/wowforever/sources/wowforevertalents.py` changed.
