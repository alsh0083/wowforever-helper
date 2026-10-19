"""Rogue poisons, part 1 (#387): the poisons' damage spells come from the client tables into the rogue's spells.
Values read by hand from SpellEffect / SpellLevels / SpellDuration of build 1.60.1.70425."""

from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.normalize import read_tables
from wowforever.normalize_spells import class_spells
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path

ROOT = Path(__file__).resolve().parents[1]
ROGUE = class_module("rogue")


def test_rogue_lists_the_poison_damage_spells():
    assert ROGUE.EXTRA_SPELLS == {
        8680: "Instant Poison", 8685: "Instant Poison", 8689: "Instant Poison", 11335: "Instant Poison",
        11336: "Instant Poison", 11337: "Instant Poison",
        2818: "Deadly Poison", 2819: "Deadly Poison", 11353: "Deadly Poison", 11354: "Deadly Poison",
        25349: "Deadly Poison"}


def test_saved_dataset_has_poison_ranks():
    spells = Dataset.load(latest_dataset_path()).class_data("rogue").spells
    instant = [s for s in spells if s.name == "Instant Poison"]
    deadly = [s for s in spells if s.name == "Deadly Poison"]
    assert [(s.rank, s.level) for s in instant] == [(1, 20), (2, 28), (3, 36), (4, 44), (5, 52), (6, 60)]
    assert [(s.rank, s.level) for s in deadly] == [(1, 30), (2, 38), (3, 46), (4, 54), (5, 60)]
    six = best_rank(spells, "Instant Poison", 60)
    # base points 88, variance 0.27692309: 88 x (1 -/+ 0.13846)
    assert (six.spell_id, six.schools) == (11337, ("nature",))
    assert six.min_damage == pytest.approx(75.815, abs=0.01) and six.max_damage == pytest.approx(100.185, abs=0.01)
    five = best_rank(spells, "Deadly Poison", 60)
    # 23 per 3 s tick over 12 s
    assert (five.spell_id, five.periodic_damage, five.tick_period, five.duration) == (25349, 92.0, 3.0, 12.0)
    assert best_rank(spells, "Instant Poison", 19) is None


@pytest.mark.skipif(not (ROOT / "data" / "cache" / "wago" / "1.60.1.70425").is_dir(), reason="client tables not cached")
def test_class_spells_reads_extra_spells():
    tables = read_tables(ROOT / "data" / "cache" / "wago" / "1.60.1.70425")
    plain = class_spells(tables, skill_lines=ROGUE.SKILL_LINES)
    extra = class_spells(tables, skill_lines=ROGUE.SKILL_LINES, extra_spells=ROGUE.EXTRA_SPELLS)
    assert not any(s.name == "Instant Poison" for s in plain)
    assert len(extra) == len(plain) + 11
    assert {s.spell_id for s in extra if s.name == "Deadly Poison"} == {2818, 2819, 11353, 11354, 25349}
