"""Add classes' EXTRA_SPELLS (#387) to saved datasets from the cached client tables.

    .venv/Scripts/python tools/add_extra_spells.py <build> [<build> ...]

Reads data/cache/wago/<build>/, runs normalize_spells.class_spells with the class's EXTRA_SPELLS, and appends
the spells the saved dataset doesn't have yet to data/datasets/<build>.json (sorted by name, rank), printing
each. Everything else in the dataset stays as saved.
"""

import dataclasses
import json
import sys
from pathlib import Path

from wowforever.classes import class_module
from wowforever.normalize import read_tables
from wowforever.normalize_spells import class_spells

ROOT = Path(__file__).resolve().parents[1]

for build in sys.argv[1:]:
    tables = read_tables(ROOT / "data" / "cache" / "wago" / build)
    path = ROOT / "data" / "datasets" / f"{build}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    added = 0
    for c in data["classes"]:
        module = class_module(c["class_name"])
        extra = getattr(module, "EXTRA_SPELLS", {})
        if not extra:
            continue
        have = {s["spell_id"] for s in c["spells"]}
        for spell in class_spells(tables, skill_lines=module.SKILL_LINES, extra_spells=extra):
            if spell.spell_id in extra and spell.spell_id not in have:
                c["spells"].append(dataclasses.asdict(spell))
                print(f"{build} {c['class_name']} {spell.name} r{spell.rank} (spell {spell.spell_id})")
                added += 1
        c["spells"].sort(key=lambda s: (s["name"], s["rank"]))
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"{build}: {added} spells added")
