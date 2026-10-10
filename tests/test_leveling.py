"""Leveling builds follow their endgame build's playstyle (owner feedback, 2026-10-07)."""

from collections import Counter
from pathlib import Path

import pytest

from wowforever.schema import latest_dataset_path
from wowforever.builds import load_builds
from wowforever.classes import CLASSES
from wowforever.melee_scenarios import main_tree
from wowforever.schema import Dataset

DS = Dataset.load(latest_dataset_path())


@pytest.mark.parametrize("class_name", CLASSES)
def test_leveling_paths_start_in_the_endgame_builds_main_tree(class_name):
    cls = DS.class_data(class_name)
    builds = {b.id: b for b in load_builds(class_name=class_name)}
    leveling = [b for b in builds.values() if b.mode == "leveling"]
    assert leveling, class_name
    for b in leveling:
        target = builds[b.levels_into].final_ids(cls)
        # home trees: the main tree, or both trees of a hybrid (15+ points each, as Fire/Frost)
        home = {tid for tree in cls.trees if sum(target.get(i, 0) for i in tree.talent_ids) >= 15
                or tree.name == main_tree(cls, target) for tid in tree.talent_ids}
        first = b.order_ids(cls)[:21]                      # the points to level 30
        share = sum(1 for t in first if t in home) / len(first)
        assert share >= 0.45, (b.id, round(share, 2))     # the playstyle shows from the start (Arcane PvP levels Frost-heavy: 0.48)
        ranks = Counter()
        for t in b.order_ids(cls):
            ranks[t] += 1
            assert sum(max(0, n - target.get(k, 0)) for k, n in ranks.items()) <= 7, b.id
