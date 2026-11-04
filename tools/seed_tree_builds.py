"""A PvE model build for every deep tree no endgame build covers yet (#460, #463).

After tools/import_sourced_builds.py a tree can have no build at all (no source publishes one), but each spec shows
its model build, and each PvP opponent kit plays its tree's build (pvp/kit_stats.py), which every report needs. The
PvE score needs no kits, so this runs before the first report: the tree's talents are filled first (best PvE score
per point, legal order), the rest topped up anywhere, and the result hill-climbed under the PvE score inside the
deep-tree archetype. Then the reports and tools/derive_slot_builds.py fill the PvP slots.

    .venv/Scripts/python tools/seed_tree_builds.py [class ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

from derive_slot_builds import top_up, write

from wowforever.builds import load_builds
from wowforever.classes import CLASSES, class_module
from wowforever.consensus import Consensus
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import pve_score, stat_table
from wowforever.rules import check_build, points_available
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.shortlist import classify, improve

ROOT = Path(__file__).resolve().parents[1]


def fill_tree(cls, tree, fn):
    """Points into `tree` one at a time, best score first, while a legal point is left there."""
    ranks: dict[int, int] = {}
    while sum(ranks.values()) < points_available(60, cls.rules):
        options = []
        for tid in tree.talent_ids:
            t = cls.talent(tid)
            if ranks.get(tid, 0) < t.max_rank:
                trial = {**ranks, tid: ranks.get(tid, 0) + 1}
                if not check_build(cls, trial, None):
                    options.append((fn(trial), -tid, trial))
        if not options:
            break
        ranks = max(options, key=lambda o: o[:2])[2]
    return ranks


def run(classes) -> int:
    arch = Consensus.load().archetypes
    ds = Dataset.load(latest_dataset_path())
    written = 0
    for c in classes:
        m = class_module(c)
        cls, _ = attach_effects(ds.class_data(c), m.TALENT_EFFECTS, m.UNMODELED)
        recognized = tuple(getattr(m, "HYBRIDS", ()))
        covered = set()
        for b in load_builds(class_name=c):
            if b.mode != "leveling" and b.variant == "PvE":
                covered.add(classify(cls, b.final_ids(cls), deep=arch["deep"], hybrid=arch["hybrid"],
                                     recognized=recognized))
        stats = stat_table(c).at(60)
        fn = lambda r, c=c, cls=cls, stats=stats: pve_score(c, stats, cls.spells, cls, r)
        for tree in cls.trees:
            archetype = f"deep {tree.name}"
            if archetype in covered:
                continue
            ranks = top_up(cls, fill_tree(cls, tree, fn), fn)
            best, _ = improve(cls, ranks, fn, archetype=archetype, deep=arch["deep"], hybrid=arch["hybrid"],
                              recognized=recognized, max_evals=400)
            if classify(cls, best, deep=arch["deep"], hybrid=arch["hybrid"], recognized=recognized) != archetype:
                print(f"{c} {archetype}: the seed left the archetype; no build written")
                continue
            names = {t.talent_id: t.name for t in cls.talents}
            slug = tree.name.lower().replace(" ", "-")
            write(c, f"{c}-{slug}-pve", archetype, "PvE", {names[t]: r for t, r in best.items() if r},
                  f"seeded from an empty tree (its talents first, then the rest) and hill-climbed under the PvE "
                  f"score (#463)")
            written += 1
    return written


if __name__ == "__main__":
    print(f"wrote {run(sys.argv[1:] or CLASSES)} builds")
