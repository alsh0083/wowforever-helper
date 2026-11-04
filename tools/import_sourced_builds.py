"""Replace each class's builds with community standards from current sources (#460).

Owner, 2026-10-31: "ditch any builds I forced you to hold onto before and only have the standards that you can
source". For every class this saves today's wowforeverbuilds.com and talentsforever.com snapshots (once; both
robots-allowed), deletes every build in config/builds/ for the class that isn't hand-made, and writes one community
build per slot that a source fills (src/wowforever/sourced.py). The model builds, model picks and leveling builds
are derived again afterwards:

    .venv/Scripts/python tools/import_sourced_builds.py [class ...]
    .venv/Scripts/python -m wowforever report --class <class>      # every class
    .venv/Scripts/python tools/derive_slot_builds.py
    .venv/Scripts/python tools/derive_model_picks.py
    .venv/Scripts/python tools/derive_leveling_builds.py <class ...>
    then the reports and the dashboard again (docs/patch-update.md).
"""
from __future__ import annotations

import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from wowforever.classes import CLASSES, class_module
from wowforever.consensus import Consensus
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.sourced import SOURCE_KEYS, Candidate, build_toml, pick
from wowforever.sources import talentsforever as tf
from wowforever.sources import wowforeverbuilds as wfb
from wowforever.sources.http import http_get

ROOT = Path(__file__).resolve().parents[1]
BUILDS = ROOT / "config" / "builds"
RAW = ROOT / "data" / "raw"


def candidates(class_name, cls, history, snapshot):
    guides = []
    for slug, guide in sorted(history[-1].guides.items()):
        if guide.class_slug != class_name:
            continue
        ranks, why = wfb.standard_build(slug, history, cls)
        if ranks is None:
            print(f"  guide left out: {why}")
            continue
        guides.append(Candidate("PvP" if "-pvp-" in slug else "PvE", ranks, "wowforeverbuilds.com", guide.url,
                                guide.title, "spec guide"))
    page, export = snapshot[class_name]
    window = tf.parse_builds_page(page)["window"]
    rows = sorted(tf.popular_builds(page, export), key=lambda row: -row["saved_total"])
    top = [Candidate(None, row["final"], "talentsforever.com", f"{tf.BASE_URL}/{class_name}/60/{row['code']}",
                     row["name"], f"top build #{row['rank']}{f' {window}' if window else ''}, saved {row['saved_total']}")
           for row in rows]
    return guides, top


def run(classes) -> int:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    wfb.fetch(http_get=http_get, raw_dir=RAW / "wowforeverbuilds" / today)
    tf.fetch(http_get=http_get, raw_dir=RAW / "talentsforever" / today)
    history = wfb.load_history(RAW / "wowforeverbuilds")
    folder = tf.latest_snapshot(RAW / "talentsforever")
    snapshot = tf.load_snapshot(folder)
    captured = f"{folder.name[:4]}-{folder.name[4:6]}-{folder.name[6:]}"
    consensus = Consensus.load()
    missing = [key for key in SOURCE_KEYS.values() if key not in consensus.sources]
    if missing:
        raise SystemExit(f"config/consensus.toml has no [sources] entry for {', '.join(missing)}")
    arch = consensus.archetypes
    ds = Dataset.load(latest_dataset_path())
    written = 0
    for class_name in classes:
        cls = ds.class_data(class_name)
        print(f"[{class_name}]")
        for path in sorted(BUILDS.glob("*.toml")):              # mage builds may have no "mage-" prefix or class
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
            if raw.get("class", "mage") == class_name and raw.get("origin", "hand") != "hand":
                path.unlink()
        guides, top = candidates(class_name, cls, history, snapshot)
        chosen, skipped = pick(cls, guides, top, deep=arch["deep"], hybrid=arch["hybrid"],
                               recognized=tuple(getattr(class_module(class_name), "HYBRIDS", ())))
        for line in skipped:
            print(f"  left out: {line}")
        for s in chosen:
            build_id, text = build_toml(class_name, s, captured)
            (BUILDS / f"{build_id}.toml").write_text(text, encoding="utf-8", newline="\n")
            print(f"  wrote {build_id}: {s.title} ({s.source}, {s.note})")
            written += 1
    return written


if __name__ == "__main__":
    print(f"{run(sys.argv[1:] or CLASSES)} community builds written")
