"""Tests for mage rotations and proc/stack talents (#57).

Expected values are built from `expected_damage` (golden-tested in #17) plus the rotation
formulas in docs/tasks/57-rotations.md, so each test pins one formula. Real fixture data,
level 60 vs a level-63 raid target unless noted.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.calc.ev import Modifiers, effective_cast_time, expected_damage
from wowforever.calc.talents import modifiers_for
from wowforever.classes.mage import LAYOUT, SKILL_LINES, TALENT_EFFECTS, UNMODELED
from wowforever.classes.mage_rotation import rotation
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells, ranks_of
from wowforever.scenarios import Character, scaled
from wowforever.sources.wowforevertalent import parse_page
from wowforever.stats import Stats

FIX = Path(__file__).parent / "fixtures"
RAW, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205"), LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
CLS, REPORT = attach_effects(RAW, TALENT_EFFECTS, UNMODELED)
SPELLS = class_spells(read_tables(FIX / "wago-1.60.1.70205-spells"), skill_lines=SKILL_LINES)
BUILDS = {b.id: b for b in load_builds()}
STATS = Stats(60, intellect=270, spirit=190, stamina=220, spell_power=150, crit_pct=6, hit_pct=3,
              mana=3600, health=2900)
A = Assumptions.load()
TARGET = 63


def spell(name):
    return ranks_of(SPELLS, name)[-1]


def char(ranks):
    return Character(60, STATS, SPELLS, CLS, ranks)


def tid(name):
    return CLS.talent_named(name).talent_id


def ev(s, mods):
    # level-scaled like the scenarios: ranks learned below 60 gain damage per level above it
    return expected_damage(scaled(s, 60), spell_power=150, crit_pct=6, hit_pct=3, caster_level=60,
                           target_level=TARGET, mods=mods)


def test_new_rules_parse_and_coverage_holds():
    assert REPORT == []
    wc = CLS.talent_named("Winter's Chill").effects
    assert [e.values for e in wc if e.kind == "crit_chance"] == [(2, 4, 6, 8, 10)]
    assert [e.values for e in CLS.talent_named("Arcane Concentration").effects
            if e.kind == "mana_cost_pct"] == [(-2, -4, -6, -8, -10)]


def test_plain_filler_matches_single_spell_model():
    fb = spell("Frostbolt")
    r = rotation(char({}), fb, target_level=TARGET, assumptions=A, sustained=True)
    assert r.dps == pytest.approx(ev(fb, Modifiers()) / fb.cast_time)
    assert r.mana_per_second == pytest.approx(fb.mana_cost / fb.cast_time)
    assert r.weaves == {}


def test_winters_chill_adds_sustained_frostbolt_crit():
    fb = spell("Frostbolt")
    r = rotation(char({tid("Winter's Chill"): 5}), fb, target_level=TARGET, assumptions=A, sustained=True)
    assert r.dps == pytest.approx(ev(fb, Modifiers(crit_chance_bonus=10)) / fb.cast_time)
    # not in short fights
    short = rotation(char({tid("Winter's Chill"): 5}), fb, target_level=TARGET, assumptions=A, sustained=False)
    assert short.dps == pytest.approx(ev(fb, Modifiers()) / fb.cast_time)


def test_fire_blast_weave():
    fireball, blast = spell("Fireball"), spell("Fire Blast")
    ranks = {tid("Wake of Fire"): 2}
    r = rotation(char(ranks), fireball, target_level=TARGET, assumptions=A, sustained=True)
    filler_dps = ev(fireball, Modifiers()) / fireball.cast_time
    per_min = 60 / (blast.cooldown - 2)                     # Wake of Fire 2/2: -2 s
    gain = ev(blast, modifiers_for(blast, CLS, ranks)) - filler_dps * 1.5
    assert r.weaves["Fire Blast"] == pytest.approx(per_min)
    assert r.dps == pytest.approx(filler_dps + per_min * gain / 60)


def test_improved_scorch_stacks_and_their_upkeep():
    fireball, scorch = spell("Fireball"), spell("Scorch")
    ranks = {tid("Improved Scorch"): 3}
    r = rotation(char(ranks), fireball, target_level=TARGET, assumptions=A, sustained=True)
    vuln = Modifiers(damage_pct=15)                          # 5 stacks x 3%
    filler_dps = ev(fireball, vuln) / fireball.cast_time
    scorches = 2 * 1 / 1.0                                   # refresh every 30 s, 100% chance at 3/3
    gain = ev(scorch, vuln) - filler_dps * scorch.cast_time
    blast = spell("Fire Blast")                              # always woven with a Fire filler
    blast_gain = ev(blast, vuln) - filler_dps * 1.5
    assert r.weaves["Scorch"] == pytest.approx(scorches)
    assert r.dps == pytest.approx(filler_dps + scorches * gain / 60
                                  + 60 / blast.cooldown * blast_gain / 60)


def test_heating_up_pyroblasts():
    fireball, pyro = spell("Fireball"), spell("Pyroblast")
    ranks = {tid("Heating Up"): 1, tid("Pyroblast"): 1}
    r = rotation(char(ranks), fireball, target_level=TARGET, assumptions=A, sustained=True)
    filler_dps = ev(fireball, Modifiers()) / fireball.cast_time
    hit, crit = 1 - 0.14, 0.06                              # +3 target: 17% - 3 hit
    casts = 60 / fireball.cast_time
    pyros = casts * hit * crit / 3                          # 3 stacks per Pyroblast
    gain = ev(pyro, Modifiers()) - filler_dps * pyro.cast_time * 0.25
    blast = spell("Fire Blast")                              # always woven with a Fire filler
    blast_gain = ev(blast, Modifiers()) - filler_dps * 1.5
    assert r.weaves["Pyroblast"] == pytest.approx(pyros)
    assert r.dps == pytest.approx(filler_dps + pyros * gain / 60 + 60 / blast.cooldown * blast_gain / 60)


def test_fingers_of_frost_frozen_ice_lances():
    fb, lance = spell("Frostbolt"), spell("Ice Lance")
    ranks = {tid("Fingers of Frost"): 2, tid("Ice Lance"): 1}
    r = rotation(char(ranks), fb, target_level=TARGET, assumptions=A, sustained=False)
    filler_dps = ev(fb, Modifiers()) / fb.cast_time
    procs = 60 / fb.cast_time * 0.15                         # every Frostbolt chills
    frozen = replace(lance, min_damage=lance.min_damage * 4, max_damage=lance.max_damage * 4,
                     coefficient=lance.coefficient * 4)     # +300% vs frozen
    gain = ev(frozen, Modifiers()) - filler_dps * 1.5
    assert r.weaves["Ice Lance"] == pytest.approx(procs * 2)
    assert r.dps == pytest.approx(filler_dps + procs * 2 * gain / 60)


def test_mana_talents():
    fb = spell("Frostbolt")
    ranks = {tid("Arcane Concentration"): 5, tid("Master of Elements"): 3}
    r = rotation(char(ranks), fb, target_level=TARGET, assumptions=A, sustained=True)
    crit_rate = 0.86 * 0.06
    cost = fb.mana_cost * (1 - 0.10) - fb.mana_cost * 0.30 * crit_rate
    assert r.mana_per_second == pytest.approx(cost / fb.cast_time)


def test_arcane_power_averages_over_its_cooldown():
    fb = spell("Frostbolt")
    r = rotation(char({tid("Arcane Power"): 1}), fb, target_level=TARGET, assumptions=A, sustained=True)
    mods = Modifiers(damage_pct=30 * 15 / 180, mana_cost_pct=30 * 15 / 180)
    assert r.dps == pytest.approx(ev(fb, mods) / fb.cast_time)
    assert r.mana_per_second == pytest.approx(fb.mana_cost * (1 + 2.5 / 100) / fb.cast_time)


def test_weaves_never_exceed_the_minute():
    r = rotation(char(BUILDS["deep-fire"].final_ids(CLS)), spell("Fireball"), target_level=TARGET,
                 assumptions=A, sustained=True)
    assert sum(n * t for n, t in zip(r.weaves.values(), r.weave_cast_times.values())) <= 60 + 1e-9
    assert r.dps > 0


def test_arcane_missiles_damage_comes_from_its_missile_spell():
    am = spell("Arcane Missiles")
    assert am.channeled and am.periodic_damage > 0
