"""A PvE model build for every deep tree and recognized hybrid no endgame build covers yet (#460, #463).

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


def fill_tree(cls, tree, fn, ranks=None, limit=None):
    """Points into `tree` one at a time, best score first, while a legal point is left there (and, with `limit`,
    until the tree holds that many)."""
    ranks = dict(ranks or {})
    total = points_available(60, cls.rules)
    while sum(ranks.values()) < total and (limit is None or sum(ranks.get(t, 0) for t in tree.talent_ids) < limit):
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
        # the mage report reads its hybrids from config/consensus.toml, the other classes from their module
        recognized = tuple(getattr(m, "HYBRIDS", arch["recognized"] if c == "mage" else ()))
        covered = set()
        for b in load_builds(class_name=c):
            if b.mode != "leveling" and b.variant == "PvE":
                covered.add(classify(cls, b.final_ids(cls), deep=arch["deep"], hybrid=arch["hybrid"],
                                     recognized=recognized))
        stats = stat_table(c).at(60)
        fn = lambda r, c=c, cls=cls, stats=stats: pve_score(c, stats, cls.spells, cls, r)
        trees = {tree.name: tree for tree in cls.trees}
        targets = [(f"deep {tree.name}", (tree,)) for tree in cls.trees]
        targets += [(hybrid, tuple(trees[n] for n in hybrid.split("/"))) for hybrid in recognized]
        for archetype, parts in targets:
            if archetype in covered:
                continue
            if len(parts) == 1:
                ranks = fill_tree(cls, parts[0], fn)
            else:                      # a hybrid: its first tree up to 30 points, then its second
                ranks = fill_tree(cls, parts[1], fn, fill_tree(cls, parts[0], fn, limit=30))
            ranks = top_up(cls, ranks, fn)
            best, _ = improve(cls, ranks, fn, archetype=archetype, deep=arch["deep"], hybrid=arch["hybrid"],
                              recognized=recognized, max_evals=400)
            if classify(cls, best, deep=arch["deep"], hybrid=arch["hybrid"], recognized=recognized) != archetype:
                print(f"{c} {archetype}: the seed left the archetype; no build written")
                continue
            names = {t.talent_id: t.name for t in cls.talents}
            slug = archetype.removeprefix("deep ").lower().replace("/", "-").replace(" ", "-")
            write(c, f"{c}-{slug}-pve", archetype, "PvE", {names[t]: r for t, r in best.items() if r},
                  f"seeded from an empty tree (its talents first, then the rest) and hill-climbed under the PvE "
                  f"score (#463)")
            written += 1
    return written


if __name__ == "__main__":
    print(f"wrote {run(sys.argv[1:] or CLASSES)} builds")
