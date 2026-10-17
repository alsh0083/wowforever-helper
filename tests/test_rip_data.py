"""Rip's damage per combo point (#397, part A): the aura's EffectPointsPerResource, over every tick.
Hand values from SpellEffect 9896 (1.60.1.70425): 15 base + 25.5 per combo point per 2 s tick, 12 s (6 ticks)."""

from pathlib import Path

import pytest

from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

ROOT = Path(__file__).resolve().parents[1]
DRUID = Dataset.load(latest_dataset_path()).class_data("druid")


def test_saved_dataset_has_rip_per_combo_point():
    rip = best_rank(DRUID.spells, "Rip", 60)
    assert (rip.spell_id, rip.tick_period, rip.duration) == (9896, 2.0, 12.0)
    assert rip.periodic_damage == pytest.approx(90.0)                 # 6 x 15
    assert rip.periodic_per_combo_point == pytest.approx(153.0)       # 6 x 25.5
    assert best_rank(DRUID.spells, "Rake", 60).periodic_per_combo_point == 0.0


@pytest.mark.skipif(not (ROOT / "data" / "cache" / "wago" / "1.60.1.70425").is_dir(), reason="client tables not cached")
def test_normalizer_reads_it():
    from wowforever.classes import class_module
    from wowforever.normalize import read_tables
    from wowforever.normalize_spells import class_spells

    spells = class_spells(read_tables(ROOT / "data" / "cache" / "wago" / "1.60.1.70425"),
                          skill_lines=class_module("druid").SKILL_LINES)
    assert best_rank(spells, "Rip", 60).periodic_per_combo_point == pytest.approx(153.0)
