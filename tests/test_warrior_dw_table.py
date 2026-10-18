"""Fury dual wield, part A (#391): a second warrior stat table whose gear picks two one-handers instead of a
two-hander (config/melee.toml [warrior_dw], config/stats/warrior_dw.csv)."""

from wowforever.melee_scenarios import MeleeStatTable
from wowforever.melee_stats import class_config


def test_config_section_dual_wields():
    dw, two = class_config("warrior_dw"), class_config("warrior")
    assert dw.get("prefer_two_hand", False) is False and two["prefer_two_hand"] is True
    for key in ("armor", "one_hand", "ranged", "ap_level", "ap_str", "ap_agi", "ap_const", "rap_level", "rap_agi",
                "rap_const", "agi_per_crit_at_60", "uses_mana", "weights"):
        assert dw[key] == two[key], key


def test_dual_wield_table_has_two_one_handers():
    table = MeleeStatTable.load("warrior_dw")
    for level in (20, 40, 60):
        row = table.at(level)
        assert row.main_hand is not None and row.off_hand is not None, level
        assert row.main_hand[2] <= 3.0 and row.off_hand[2] <= 3.0          # one-hand speeds
    two = MeleeStatTable.load("warrior").at(60)
    assert two.off_hand is None and two.main_hand[2] > 3.0               # the Arms table keeps its two-hander
