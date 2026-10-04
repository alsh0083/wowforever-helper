import pytest

from wowforever.stats import Stats, StatTable


def anchor(level, sp):
    return Stats(level, 0, 0, 0, sp, 0, 0, 0, 0)


def test_interpolates_between_anchors():
    table = StatTable([anchor(10, 0), anchor(20, 10)])
    assert table.at(15).spell_power == pytest.approx(5)
    assert table.at(15).level == 15


def test_clamps_outside_range():
    table = StatTable([anchor(10, 0), anchor(20, 10)])
    assert table.at(5).spell_power == 0
    assert table.at(60).spell_power == 10
    assert table.at(60).level == 60


def test_rejects_duplicate_levels():
    with pytest.raises(ValueError, match="duplicate"):
        StatTable([anchor(10, 0), anchor(10, 1)])


def test_shipped_mage_table_covers_10_to_60_and_is_monotonic():
    table = StatTable.load("mage")
    rows = [table.at(level) for level in range(10, 61)]
    assert [a.level for a in table.anchors][0] == 10 and table.anchors[-1].level == 60
    for prev, cur in zip(rows, rows[1:]):
        assert cur.spell_power >= prev.spell_power
        assert cur.mana >= prev.mana
        assert cur.crit_pct >= prev.crit_pct
