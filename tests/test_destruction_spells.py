"""Warlock "Destruction spells" are the Destruction skill line, Shadow Bolt included (#377)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from test_group import _engine  # noqa: E402

from wowforever.assumptions import Assumptions  # noqa: E402
from wowforever.calc.talents import modifiers_for  # noqa: E402
from wowforever.caster import cast, talent_stats  # noqa: E402
from wowforever.scenarios import best_rank  # noqa: E402


def test_destruction_spells_come_from_the_skill_line():
    from wowforever.classes.warlock import DESTRUCTION_SPELLS

    # client SkillLineAbility, skill line 593 (Destruction), damaging spells (wago 1.60.1.70425)
    assert set(DESTRUCTION_SPELLS) == {"Conflagrate", "Hellfire", "Immolate", "Incinerate", "Rain of Fire",
                                       "Searing Pain", "Shadow Bolt", "Shadowburn", "Soul Fire"}


def test_shadow_bolt_gets_ruin_agonizing_flames_and_cataclysm():
    stats, cls, ranks = _engine("warlock", "warlock-destruction-pve")
    bolt = best_rank(cls.spells, "Shadow Bolt", 60)
    m = modifiers_for(bolt, cls, ranks)
    # Demonic Sacrifice 15 + Shadow and Flame 10 + Agonizing Flames 10; Ruin +100% crit damage; Cataclysm -10% mana
    assert m.damage_pct == pytest.approx(35.0) and m.crit_damage_bonus_pct == pytest.approx(100.0)
    assert m.mana_cost_pct == pytest.approx(-10.0)


def test_shadow_bolt_by_hand():
    stats, cls, ranks = _engine("warlock", "warlock-destruction-pve")
    bolt = best_rank(cls.spells, "Shadow Bolt", 60)            # learned at 60: no level scaling
    st = talent_stats("warlock", stats, cls, ranks)
    ev, seconds, _ = cast(bolt, st, cls, ranks, 60, Assumptions.load())
    avg = (bolt.min_damage + bolt.max_damage) / 2 + bolt.coefficient * st.spell_power
    hit = 0.99                                                   # 4% base miss, hit 2.79 + Suppression: floor 1%
    crit = st.crit_pct / 100
    assert ev == pytest.approx(hit * avg * 1.35 * (1 + crit * 0.5 * 2.0))   # crit bonus 50% x (1 + Ruin 100%)
    assert seconds == pytest.approx(2.5)                         # 3.0 s - Bane 0.5 s
