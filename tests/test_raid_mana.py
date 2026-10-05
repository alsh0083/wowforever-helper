"""Raid mana budget from Forever numbers (#78): consumables, Evocation, spirit regen while casting,
fight-length mix, and mana-limited casting after OOM. Spec: docs/tasks/78-raid-mana.md.

Synthetic setup as in test_scenarios.py: no talents, 0 spell power/crit/hit, level 60 vs 63
(17% miss). Fireball rank 2: 1000 damage, 2.5 s, 400 mana -> 332 DPS, 160 mana/s.
"""

from pathlib import Path

import pytest

from wowforever.assumptions import Assumptions
from wowforever.classes.mage import LAYOUT, TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells
from wowforever.classes.mage import SKILL_LINES
from wowforever.scenarios import Character, RaidParams, combat_regen, default_params, raid, spirit_regen
from wowforever.schema import ClassData, SpellRank
from wowforever.sources.wowforevertalent import parse_page
from wowforever.stats import Stats

EMPTY = ClassData("testclass", (), ())
A = Assumptions.load()
NUKE1 = SpellRank(4, "Fireball", 1, 50, ("fire",), 2.5, mana_cost=200, min_damage=600, max_damage=600)
NUKE = SpellRank(3, "Fireball", 2, 60, ("fire",), 2.5, mana_cost=400, min_damage=1000, max_damage=1000)


def char(spirit=0, spells=(NUKE,)):
    stats = Stats(60, intellect=0, spirit=spirit, stamina=0, spell_power=0, crit_pct=0, hit_pct=0,
                  mana=4000, health=1000)
    return Character(60, stats, spells, EMPTY, {})


def params(**kw):
    return RaidParams(fight_seconds=180, mana_per_second=kw.pop("mana_per_second", 0),
                      fillers=("Fireball",), **kw)


def test_spirit_regen_is_the_classic_mage_formula():
    assert spirit_regen(char(spirit=132).stats) == pytest.approx(23.0)   # (13 + 132 / 4) / 2


def test_consumables_add_mana_once_per_cooldown_in_the_fight():
    # 180 s fight, 2 min potion -> 2 uses: (4000 + 3600) / 160 = 47.5 s
    r = raid(char(), params(consumables=((1800, 120),)), A)
    assert r.details["time_to_oom"] == pytest.approx(47.5)
    assert r.score == pytest.approx(332 * 47.5 / 180)
    assert r.details["dps"] == pytest.approx(332)


def test_evocation_refills_from_spirit_and_costs_its_channel():
    # Evocation: 23 mana/s x 16 x 8 s = 2944; (4000 + 2944) / 160 = 43.4 s casting, 8 s channel
    r = raid(char(spirit=132), params(spirit_regen=True, evocation=True), A)
    assert r.details["evocation_used"] is True
    assert r.details["time_to_oom"] == pytest.approx(43.4 + 8)
    assert r.score == pytest.approx(332 * 43.4 / 180)


def test_evocation_is_skipped_when_regen_covers_the_rotation():
    r = raid(char(spirit=132), params(mana_per_second=500, spirit_regen=True, evocation=True), A)
    assert r.details["evocation_used"] is False
    assert r.details["time_to_oom"] is None
    assert r.score == pytest.approx(332)


def test_fallback_keeps_casting_at_the_mana_limited_rate():
    # drain 160 - 40 = 120 -> OOM at 33.33 s; then 40 mana/s buys 40/160 of full DPS = 83
    t_full = 4000 / 120
    r = raid(char(), params(mana_per_second=40, fallback=True), A)
    assert r.score == pytest.approx((332 * t_full + 83 * (180 - t_full)) / 180)
    assert r.details["fallback_spell"] == "Fireball rank 2"


def test_fallback_downranks_when_a_cheaper_rank_does_more_per_mana():
    # rank 1: 0.83 * 600 / 2.5 = 199.2 DPS at 80 mana/s -> 40 mana/s buys half = 99.6 > 83
    t_full = 4000 / 120
    r = raid(char(spells=(NUKE1, NUKE)), params(mana_per_second=40, fallback=True), A)
    assert r.details["spell"] == "Fireball"
    assert r.details["fallback_spell"] == "Fireball rank 1"
    assert r.score == pytest.approx((332 * t_full + 99.6 * (180 - t_full)) / 180)


def test_no_fallback_means_zero_after_oom():
    r = raid(char(), params(mana_per_second=40), A)
    assert r.details["fallback_spell"] is None
    assert r.score == pytest.approx(332 * (4000 / 120) / 180)


def test_score_is_the_weighted_mean_over_fight_lengths():
    # OOM at 25 s in both: 332*25/90 and 332*25/270, equal weights
    r = raid(char(), params(fight_lengths=((90, 1), (270, 1))), A)
    assert r.score == pytest.approx((332 * 25 / 90 + 332 * 25 / 270) / 2)
    assert set(r.details["by_length"]) == {90, 270}


# Arcane Meditation, from the real Forever rank text (17/33/50%)
FIX = Path(__file__).parent / "fixtures"
RAW, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205"), LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
CLS, _ = attach_effects(RAW, TALENT_EFFECTS, UNMODELED)
SPELLS = class_spells(read_tables(FIX / "wago-1.60.1.70205-spells"), skill_lines=SKILL_LINES)


def test_arcane_meditation_lets_half_of_spirit_regen_continue_while_casting():
    am = CLS.talent_named("Arcane Meditation")
    stats = Stats(60, intellect=270, spirit=190, stamina=220, spell_power=150, crit_pct=6, hit_pct=3,
                  mana=3600, health=2900)
    p = RaidParams(fight_seconds=180, mana_per_second=8, fillers=("Frostbolt",), spirit_regen=True)
    with_am = Character(60, stats, SPELLS, CLS, {am.talent_id: 3})
    without = Character(60, stats, SPELLS, CLS, {})
    assert combat_regen(with_am, p) == pytest.approx(8 + (13 + 190 / 4) / 2 * 0.5)
    assert combat_regen(without, p) == pytest.approx(8)
    assert "Arcane Meditation" not in UNMODELED


def test_default_params_carry_the_forever_budget():
    r = default_params("raid", 60)
    assert r.fight_lengths == ((90, 1), (180, 2), (300, 1))
    assert r.consumables == ((1800, 120), (1200, 120))
    assert r.extra_mana == 1100 and r.mana_per_second == 8
    assert r.evocation and r.spirit_regen and r.fallback
    d = default_params("dungeon", 60)
    assert not d.evocation and d.consumables == () and d.fallback

