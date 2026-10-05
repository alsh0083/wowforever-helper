"""Tests for talent effects (#51): numbers parsed from Forever rank text, and Modifiers per spell.

Expected values are read off the rank text printed by the normalizer on the real fixtures
(build 1.60.1.70205 / wowforevertalent.com 70170).
"""

from pathlib import Path

import pytest

from wowforever.builds import load_builds
from wowforever.calc.ev import Modifiers, expected_damage
from wowforever.calc.talents import modifiers_for
from wowforever.classes.mage import LAYOUT, TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.schema import Dataset, Provenance, SpellRank
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
RAW, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205"), LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
CLS, REPORT = attach_effects(RAW, TALENT_EFFECTS, UNMODELED)
BUILDS = {b.id: b for b in load_builds()}

FIREBALL = SpellRank(25306, "Fireball", 12, 60, ("fire",), 3.5, mana_cost=410,
                     min_damage=596, max_damage=760, coefficient=1.0)
FROSTBOLT = SpellRank(25304, "Frostbolt", 11, 60, ("frost",), 3.0, mana_cost=290,
                      min_damage=457.24, max_damage=492.76, coefficient=0.814)
ICE_LANCE = SpellRank(1240047, "Ice Lance", 6, 56, ("frost",), 0.0, mana_cost=150,
                      min_damage=170, max_damage=190, coefficient=0.143)


def values(name, kind):
    (effect,) = [e for e in CLS.talent_named(name).effects if e.kind == kind]
    return effect.values


def test_every_talent_is_either_modeled_or_listed_as_unmodeled():
    names = {t.name for t in CLS.talents}
    assert set(TALENT_EFFECTS) | set(UNMODELED) == names
    assert not set(TALENT_EFFECTS) & set(UNMODELED)
    assert REPORT == []                                   # every pattern matched every rank


@pytest.mark.parametrize("name, kind, expected", [
    ("Ignite", "dot_pct", (8, 16, 24, 32, 40)),
    ("Critical Mass", "crit_chance", (2, 4, 6)),
    ("Fire Power", "damage_pct", (2, 4, 6, 8, 10)),
    ("Improved Fireball", "cast_time", (-0.1, -0.2, -0.3, -0.4, -0.5)),
    ("Incineration", "crit_chance", (2, 4, 6)),
    ("Ice Shards", "crit_damage_pct", (20, 40, 60, 80, 100)),
    ("Piercing Ice", "damage_pct", (2, 4, 6)),
    ("Elemental Precision", "hit_chance", (1, 2, 3, 4, 5)),
    ("Frost Channeling", "mana_cost_pct", (-5, -10, -15)),
    ("Arcane Instability", "damage_pct", (1, 2, 3)),
    ("Arcane Instability", "crit_chance", (1, 2, 3)),
    ("Impact", "proc_chance", (3, 7, 10)),
    ("Burning Soul", "pushback_pct", (23, 47, 70)),
    ("Shatter", "crit_chance", (17, 33, 50)),
])
def test_values_per_rank_parsed_from_rank_text(name, kind, expected):
    assert values(name, kind) == pytest.approx(expected)


def test_applies_to_and_conditions():
    (shatter,) = CLS.talent_named("Shatter").effects
    assert shatter.applies_to == ("all", "@frozen")
    (imp_fb,) = CLS.talent_named("Improved Fireball").effects
    assert set(imp_fb.applies_to) == {"Fireball", "Frostfire Bolt"}


def ranks(build_id):
    return BUILDS[build_id].final_ids(CLS)


def test_modifiers_for_fireball_in_current_elementalist_route():
    # Critical Mass 3/3 (+6 crit), Ignite 5/5 (40), Improved Fireball 5/5 (-0.5 s),
    # Elemental Precision 2/5 (+2 hit). Incineration doesn't list Fireball; no Fire Power.
    assert modifiers_for(FIREBALL, CLS, ranks("elementalist-v4")) == Modifiers(
        crit_chance_bonus=6, ignite_pct=40, cast_time_delta=-0.5, hit_bonus=2)


def test_modifiers_for_frostbolt_in_deep_frost():
    # Piercing Ice +6% damage, Ice Shards +100 crit damage, Improved Frostbolt -0.5 s,
    # Elemental Precision +5 hit, Frost Channeling -15% mana. Shatter only vs frozen targets.
    assert modifiers_for(FROSTBOLT, CLS, ranks("deep-frost")) == Modifiers(
        damage_pct=6, crit_damage_bonus_pct=100, cast_time_delta=-0.5, mana_cost_pct=-15, hit_bonus=5)
    assert modifiers_for(FROSTBOLT, CLS, ranks("deep-frost"), conditions={"frozen"}).crit_chance_bonus == 50


def test_untaken_talents_with_rank_zero_add_nothing():
    zeros = {t: 0 for t in ranks("deep-frost")}
    assert modifiers_for(FROSTBOLT, CLS, zeros) == Modifiers()


def test_incineration_applies_to_ice_lance_by_name():
    # the Elementalist has Incineration 3/3 and Ice Shards 5/5
    m = modifiers_for(ICE_LANCE, CLS, ranks("elementalist-v4"))
    assert m.crit_chance_bonus == 6 and m.crit_damage_bonus_pct == 100


def test_damage_pct_stacks_additively():
    # Deep Arcane has Arcane Instability 3/3 and no Fire damage talents: +3% damage, +3 crit
    m = modifiers_for(FIREBALL, CLS, ranks("deep-arcane"))
    assert (m.damage_pct, m.crit_chance_bonus) == (3, 3)


def test_hit_bonus_feeds_expected_damage():
    base = dict(spell_power=0, crit_pct=0, hit_pct=0, caster_level=60, target_level=63)
    no_hit = expected_damage(FROSTBOLT, mods=Modifiers(), **base)
    with_hit = expected_damage(FROSTBOLT, mods=Modifiers(hit_bonus=5), **base)
    # miss 17% -> 12%: ratio 0.88 / 0.83
    assert with_hit / no_hit == pytest.approx(0.88 / 0.83)


def test_effects_survive_a_dataset_round_trip(tmp_path):
    prov = Provenance("wago.tools", "1.60.1.70205", "1.60.1.70205", "2026-10-04T00:00:00Z", "0" * 64)
    ds = Dataset("1.60.1.70205", "1.60.1.70205", (CLS,), (prov,))
    ds.validate()
    ds.save(tmp_path / "ds.json")
    assert Dataset.load(tmp_path / "ds.json") == ds
