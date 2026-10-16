"""Fill `mana_cost_pct` (#361) into saved datasets from the cached client SpellPower table.

    .venv/Scripts/python tools/backfill_mana_cost_pct.py <build> [<build> ...]

wago's SpellPower gives some spells' cost as a percentage of base mana (PowerCostPct, ManaCost 0); datasets
saved before #361 lack it. Reads data/cache/wago/<build>/SpellPower.csv and writes data/datasets/<build>.json
in Dataset.save's format; the JSON is edited directly so Dataset.class_data's cost resolution isn't saved.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for build in sys.argv[1:]:
    pct = {}
    with (ROOT / "data" / "cache" / "wago" / build / "SpellPower.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["PowerType"] == "0" and float(row["PowerCostPct"] or 0):
                pct[int(row["SpellID"])] = float(row["PowerCostPct"])
    path = ROOT / "data" / "datasets" / f"{build}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for c in data["classes"]:
        for spell in c["spells"]:
            spell["mana_cost_pct"] = pct.get(spell["spell_id"], 0.0)
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"{build}: {len(pct)} percentage costs")
