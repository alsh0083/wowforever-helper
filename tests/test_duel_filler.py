"""Duels pick their own filler; Frost Nova into Shatter against melee (#97).
Spec: docs/tasks/97-duel-filler.md. Real fixture data as in test_rotation.py."""

from dataclasses import replace
from pathlib import Path

import pytest

from wowforever.assumptions import Assumptions
from wowforever.calc.ev import GCD_SECONDS, Modifiers, expected_damage
from wowforever.classes.mage import LAYOUT, SKILL_LINES, TALENT_EFFECTS, UNMODELED
from wowforever.classes.mage_rotation import frozen_hit_gain
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells, ranks_of
from wowforever.pvp.duel import (Control, Kit, MageSide, best_scenario_scores, duel, load_kits,
                                 mage_side, scenario_scores)
from wowforever.scenarios import Character, scaled, usable_fillers
from wowforever.sources.wowforevertalent import parse_page
from wowforever.stats import Stats

FIX = Path(__file__).parent / "fixtures"
RAW, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205"), LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
CLS, _ = attach_effects(RAW, TALENT_EFFECTS, UNMODELED)
SPELLS = class_spells(read_tables(FIX / "wago-1.60.1.70205-spells"), skill_lines=SKILL_LINES)
STATS = Stats(60, intellect=270, spirit=190, stamina=220, spell_power=150, crit_pct=6, hit_pct=3,
              mana=3600, health=2900)
A = Assumptions.load()


def tid(name):
    return CLS.talent_named(name).talent_id


def spell(name):
    return ranks_of(SPELLS, name)[-1]


def char(ranks):
    return Character(60, STATS, SPELLS, CLS, ranks)


def ev(s, mods):
    # same-level duel target: 4% base miss - 3% hit = 1% miss
    return expected_damage(scaled(s, 60), spell_power=150, crit_pct=6, hit_pct=3, caster_level=60,
                           target_level=60, mods=mods)


def test_usable_fillers_keep_names_order_and_skip_unlearned():
    c = char({})
    names = ("Frostbolt", "Fireball", "Frostfire Bolt", "Arcane Missiles")
    got = usable_fillers(c, names, 60, A)
    assert [s.name for s in got] == [n for n in names if n in {s.name for s in got}]
    assert got[0] == spell("Frostbolt") and got[1] == spell("Fireball")


def test_frozen_hit_without_ice_lance_is_a_shatter_crit_filler():
    fb = spell("Frostbolt")
    c = char({tid("Shatter"): 3})
    gain = frozen_hit_gain(c, fb, target_level=60, assumptions=A)
    assert gain == pytest.approx(ev(fb, Modifiers(crit_chance_bonus=50)) - ev(fb, Modifiers()))


def test_frozen_hit_without_shatter_or_ice_lance_gains_nothing():
    assert frozen_hit_gain(char({}), spell("Frostbolt"), target_level=60, assumptions=A) == pytest.approx(0)


def test_frozen_hit_with_ice_lance_replaces_filler_time():
    fb, lance = spell("Frostbolt"), spell("Ice Lance")
    c = char({tid("Shatter"): 3, tid("Ice Lance"): 1})
    frozen = replace(lance, min_damage=lance.min_damage * 4, max_damage=lance.max_damage * 4,
                     coefficient=lance.coefficient * 4)
    expected = ev(frozen, Modifiers(crit_chance_bonus=50)) - ev(fb, Modifiers()) / fb.cast_time * GCD_SECONDS
    assert frozen_hit_gain(c, fb, target_level=60, assumptions=A) == pytest.approx(expected)


def test_mage_side_adds_one_frozen_hit_per_frost_nova():
    fb = spell("Frostbolt")
    c = char({tid("Shatter"): 3, tid("Ice Lance"): 1, tid("Improved Frost Nova"): 2})
    side = mage_side(c, fb)
    nova_cd = spell("Frost Nova").cooldown - 4                       # Improved Frost Nova 2/2
    assert side.nova_dps == pytest.approx(frozen_hit_gain(c, fb, target_level=60, assumptions=A) / nova_cd)


MAGE = MageSide(health=3000, dps=150, barrier_per_min=0, immunity_share=0, root=20, stun=0,
                slow=0.5, interrupt=20, nova_dps=30)
MELEE = Kit(id="m", role="melee", stealth=False, dispels_buffs=False, health=4000, dps=200,
            opener_damage=0, opener_stun=0, controls=(), removes=(), immunity=None)
CASTER = replace(MELEE, id="c", role="caster")


def test_nova_damage_counts_only_against_melee():
    assert duel(MAGE, MELEE, "mage_sees").t_mage == pytest.approx(4000 / 180)
    assert duel(MAGE, CASTER, "mage_sees").t_mage == pytest.approx(4000 / 150)


def test_each_scenario_takes_its_best_filler():
    c = char({tid("Shatter"): 3, tid("Ice Lance"): 1, tid("Frostbite"): 3, tid("Ignite"): 5})
    kits = load_kits()
    fillers = usable_fillers(c, ("Frostbolt", "Fireball"), 60, A)
    per_filler = {f.name: scenario_scores(mage_side(c, f), kits) for f in fillers}
    best = best_scenario_scores(c, fillers, kits)
    for scenario, result in best.items():
        top = max(per_filler, key=lambda n: per_filler[n][scenario]["score"])
        assert result["spell"] == top
        assert result["score"] == pytest.approx(per_filler[top][scenario]["score"])
