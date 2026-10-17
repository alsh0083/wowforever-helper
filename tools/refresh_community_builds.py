"""Refresh hand-adjusted community builds from post-patch popularity data (#369).

    .venv/Scripts/python tools/refresh_community_builds.py            # report the closest post-patch builds
    .venv/Scripts/python tools/refresh_community_builds.py --write    # rewrite the build files

For every endgame community build with an `adjusted` mark (points Claude moved for a new game build), the
closest post-patch popular build in the same tree (data/popularity/<class>.json, from the update check) replaces
its talents. Re-derive the leveling builds afterwards: tools/derive_leveling_builds.py <class ...>.
"""

import json
import sys
from datetime import date
from pathlib import Path

from wowforever.builds import load_builds
from wowforever.classes import CLASSES
from wowforever.community import closest_popular, refresh_status, refreshed_toml
from wowforever.schema import Dataset, latest_dataset_path

ROOT = Path(__file__).resolve().parents[1]
WRITE = "--write" in sys.argv
DS = Dataset.load(latest_dataset_path())
# a match must keep the build recognisable: most of its 51 points in common; weaker matches stay adjusted
MIN_OVERLAP = 45

for c in CLASSES:
    path = ROOT / "data" / "popularity" / f"{c}.json"
    if not path.exists():
        continue
    pop = json.loads(path.read_text(encoding="utf-8"))
    cls = DS.class_data(c)
    for b in load_builds(class_name=c):
        file = ROOT / "config" / "builds" / f"{b.id}.toml"
        refreshed_before = "# refreshed from" in file.read_text(encoding="utf-8")
        if b.mode != "endgame" or b.origin != "community" or not (b.adjusted or b.provisional or b.refreshed
                                                                  or refreshed_before):
            continue
        if not any(s.startswith("wft_popular") for s in b.sources):
            # a catalog plan (wft_builds_*): re-import it with tools/import_wft_builds.py instead
            print(f"{b.id}: catalog plan, re-import it (stays adjusted)")
            continue
        match = closest_popular(b, cls, pop["top"])
        if match is None:
            print(f"{b.id}: no post-patch build in this tree (stays adjusted)")
            continue
        weak = bool(b.adjusted) and match["overlap"] < MIN_OVERLAP
        status = refresh_status(b, match)
        print(f"{b.id}: {status}, rank {match['rank']}, saved {match['saved']}, points {match['points']}, "
              f"overlap {match['overlap']}" + (" - too different, stays adjusted" if weak else ""))
        if WRITE and not weak and status in ("moved", "settled"):
            file.write_text(refreshed_toml(file.read_text(encoding="utf-8"), match, window=pop["sourceWindow"],
                                           today=date.today().isoformat()), encoding="utf-8", newline="\n")
