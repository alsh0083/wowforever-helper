"""Model picks as builds next to the community standard they improve on (owner request, 2026-10-07).

    .venv/Scripts/python tools/derive_model_picks.py

For every spec-matrix slot whose standard is a community build and whose report has a model pick
(the hill-climbed variant of the standard that scores higher), writes the pick as a model build,
`<standard id>-model`, so the slot shows the community standard and the model's alternative side by
side. Rerun the class reports afterwards. Picks that are no longer better are not removed: delete
the file by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

from wowforever.builds import load_builds
from wowforever.classes import CLASSES

ROOT = Path(__file__).resolve().parents[1]


def run() -> int:
    written = 0
    for c in CLASSES:
        report = json.loads((ROOT / "data" / ("report.json" if c == "mage" else f"report-{c}.json"))
                            .read_text(encoding="utf-8"))
        builds = {b.id: b for b in load_builds(class_name=c)}
        for slot in report["shortlist"]:
            std = builds.get(slot.get("standard") or "")
            if std is None or std.origin != "community" or not slot.get("model_pick"):
                continue
            gain = (slot["model_pick_score"] / slot["standard_score"] - 1) * 100
            name = std.name.replace(f"({slot['focus']})", f"({slot['focus']}, model pick)")
            build_id = f"{std.id}-model"
            changes = ", ".join(f"{ch['talent']} {ch['from']}->{ch['to']}" for ch in slot.get("model_pick_changes", []))
            lines = [f"# Model pick for the {slot['archetype']} {slot['focus']} slot (owner request, 2026-10-07): the",
                     f"# community standard {std.id} hill-climbed under the {slot['focus']} score, {gain:+.1f}%.",
                     f"# Changes: {changes}.", "",
                     f'id = "{build_id}"', f'class = "{c}"', f'name = "{name}"', f'pair = "{build_id}"',
                     f'variant = "{slot["focus"]}"', 'origin = "model"', 'sources = []', 'confidence = "low"',
                     f'summary = "The model\'s alternative to {std.name}: {changes}. Scores {gain:+.1f}% higher; '
                     f'not tried in game."', "", "[final]"]
            lines += [f'"{n}" = {r}' for n, r in sorted(dict(slot["model_pick"]).items())]
            (ROOT / "config" / "builds" / f"{build_id}.toml").write_text("\n".join(lines) + "\n", encoding="utf-8",
                                                                         newline="\n")
            print(f"wrote {build_id}: {gain:+.1f}% ({changes})")
            written += 1
    return written


if __name__ == "__main__":
    print(f"wrote {run()} builds")
