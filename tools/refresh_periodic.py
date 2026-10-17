"""Re-derive spells' periodic damage (#382) in saved datasets from the cached client tables.

    .venv/Scripts/python tools/refresh_periodic.py <build> [<build> ...]

Datasets saved before #382 read leech DoTs (aura 53: Devouring Plague, Siphon Life, Drain Life) as 0 damage.
Reads data/cache/wago/<build>/, runs normalize_spells.class_spells for every class, and writes only the
periodic fields (periodic_damage, periodic_coefficient, tick_period) of spells whose values changed into
data/datasets/<build>.json, printing each change. Everything else in the dataset stays as saved.
"""

import json
import sys
from pathlib import Path

from wowforever.classes import CLASSES, class_module
from wowforever.normalize import read_tables
from wowforever.normalize_spells import class_spells

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("periodic_damage", "periodic_coefficient", "tick_period")

for build in sys.argv[1:]:
    tables = read_tables(ROOT / "data" / "cache" / "wago" / build)
    path = ROOT / "data" / "datasets" / f"{build}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for c in data["classes"]:
        fresh = {s.spell_id: s for s in class_spells(tables, skill_lines=class_module(c["class_name"]).SKILL_LINES)}
        for spell in c["spells"]:
            new = fresh.get(spell["spell_id"])
            if new is None:
                continue
            diff = {f: (spell.get(f), getattr(new, f)) for f in FIELDS if spell.get(f) != getattr(new, f)}
            if diff:
                print(f"{build} {c["class_name"]} {spell['name']} r{spell['rank']}: {diff}")
                spell.update({f: v for f, (_, v) in diff.items()})
                changed += 1
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"{build}: {changed} spells changed")
