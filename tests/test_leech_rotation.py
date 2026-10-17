"""The warlock rotation casts Siphon Life and can channel Drain Life (#382)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from test_group import _engine  # noqa: E402

from wowforever.assumptions import Assumptions  # noqa: E402
from wowforever.caster import caster_rotation, cast, talent_stats  # noqa: E402
from wowforever.physical import Target  # noqa: E402
from wowforever.scenarios import Character, best_rank  # noqa: E402


def test_rotation_lists_the_leech_spells():
    from wowforever.classes.warlock import ROTATION

    assert "Siphon Life" in ROTATION["dots"]
    assert "Drain Life" in ROTATION["fillers"]


def test_affliction_keeps_siphon_life_up():
    stats, cls, ranks = _engine("warlock", "warlock-affliction")
    spells = Character(60, stats, cls.spells, cls, ranks).spells
    assert "Siphon Life" in caster_rotation("warlock", stats, spells, cls, ranks, Target(3, 0)).spells


def test_siphon_life_by_hand():
    stats, cls, ranks = _engine("warlock", "warlock-affliction")
    siphon = best_rank(cls.spells, "Siphon Life", 60)         # rank 4: 410 over 30 s, 0.5 of spell power
    st = talent_stats("warlock", stats, cls, ranks)
    ev, seconds, _ = cast(siphon, st, cls, ranks, 63, Assumptions.load())
    # (410 + 0.5 x 294) x 1.25 (Demonic Sacrifice 15 + Shadow Mastery 10); a +3 target: 17% miss
    # minus 2.79 hit and Suppression 5 leaves 90.79% hit; periodic damage doesn't crit
    assert ev == pytest.approx((410 + 0.5 * 294) * 1.25 * 0.9079, rel=1e-3)
    assert seconds == 1.5
