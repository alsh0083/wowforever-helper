"""Dungeon levels for the Forever Logs comparison (#172): every dungeon with beta parses has one."""

import tomllib
from pathlib import Path

LEVELS = tomllib.loads((Path(__file__).resolve().parent.parent / "config" / "log_levels.toml").read_text(encoding="utf-8"))


def test_city_of_dalaran_and_the_stockade_have_levels():
    # City of Dalaran (new in the Oct 8 beta patch): Forever 28-33, beta capped at 30, so parses come from 28-30
    assert LEVELS["City of Dalaran"] == 29
    # The Stockade: Classic 22-30, the same range as Shadowfang Keep
    assert LEVELS["The Stockade"] == LEVELS["Shadowfang Keep"] == 25


def test_levels_stay_within_the_beta_cap():
    assert all(10 <= level <= 30 for level in LEVELS.values())
