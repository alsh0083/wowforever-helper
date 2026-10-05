"""Print every talent of a class with its last rank's text, for classification tasks:

    .venv/Scripts/python tools/list_talents.py warrior

Reads the trimmed test fixtures (tests/fixtures/wago-1.60.1.70205-<class>, wowforevertalent/<class>.html).
"""

import sys
from pathlib import Path

from wowforever.classes import class_module
from wowforever.normalize import normalize_class, read_tables
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures"

name = sys.argv[1]
module = class_module(name)
page = parse_page((FIX / "wowforevertalent" / f"{name}.html").read_text(encoding="utf-8"))
cls, _ = normalize_class(read_tables(FIX / f"wago-1.60.1.70205-{name}"), module.LAYOUT, page, wago_build="x")
trees = {t.tree_id: t.name for t in cls.trees}
for t in cls.talents:
    text = t.rank_text[-1].replace("\n", " ")[:200] if t.rank_text else "(no rank text)"
    print(f"{trees[t.tree_id]} | {t.name} | {text}")
