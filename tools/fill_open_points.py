"""Fill the points a community build leaves unspent at 60 (owner request, 2026-10-07).

    .venv/Scripts/python tools/fill_open_points.py

Some community builds spend fewer than 51 points, usually because the site's build has points in
talents the client's tree doesn't have. For each, the open points go one at a time to the legal
talent that raises the build's focus score most (the PvE score for builds without one, e.g. tanks),
and are written as a `[model_filled]` table: `[final]` stays as the community published it. Rerun
the class reports afterwards.
"""

from __future__ import annotations

from pathlib import Path

from wowforever.builds import load_builds
from wowforever.classes import CLASSES, class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import pve_score, stat_table
from wowforever.pvp.class_pvp import pvp_score
from wowforever.pvp.duel import load_kits
from wowforever.rules import check_build, points_available
from wowforever.schema import Dataset, latest_dataset_path

ROOT = Path(__file__).resolve().parents[1]
DS = Dataset.load(latest_dataset_path())


def run() -> int:
    kits = load_kits()
    written = 0
    for c in CLASSES:
        if c == "mage":
            continue  # every mage build spends all its points
        m = class_module(c)
        cls, _ = attach_effects(DS.class_data(c), m.TALENT_EFFECTS, m.UNMODELED)
        stats = stat_table(c).at(60)
        total = points_available(60, cls.rules)
        for b in load_builds(class_name=c):
            if b.origin != "community" or b.model_filled or sum(b.final.values()) >= total:
                continue
            focus = b.variant if b.variant in ("PvE", "PvP") else "PvE"
            fn = ((lambda r: pvp_score(c, stats, cls.spells, cls, r, kits)) if focus == "PvP"
                  else (lambda r: pve_score(c, stats, cls.spells, cls, r)))
            ranks = b.final_ids(cls)
            added: dict[int, int] = {}
            while sum(ranks.values()) < total:
                options = []
                for t in cls.talents:
                    if ranks.get(t.talent_id, 0) < t.max_rank:
                        trial = {**ranks, t.talent_id: ranks.get(t.talent_id, 0) + 1}
                        if not check_build(cls, trial, None):
                            options.append((fn(trial), -t.row, -t.talent_id, t.talent_id, trial))
                if not options:
                    break
                *_, tid, ranks = max(options, key=lambda o: o[:3])
                added[tid] = added.get(tid, 0) + 1
            names = {t.talent_id: t.name for t in cls.talents}
            filled = {names[t]: r for t, r in sorted(added.items(), key=lambda kv: names[kv[0]])}
            path = ROOT / "config" / "builds" / f"{b.id}.toml"
            text = path.read_text(encoding="utf-8").rstrip("\n")
            text += ("\n\n# The community build spends fewer than 51 points (owner request, 2026-10-07): the model\n"
                     f"# fills the rest with the best legal talents under the {focus} score. [final] is as published.\n"
                     "[model_filled]\n" + "".join(f'"{n}" = {r}\n' for n, r in filled.items()))
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"{b.id}: +{sum(added.values())} ({', '.join(f'{n} {r}' for n, r in filled.items())})")
            written += 1
    return written


if __name__ == "__main__":
    print(f"filled {run()} builds")
