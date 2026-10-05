"""Hunter damage talents as effect rules (#132, part 1). Spec: docs/tasks/132-hunter-effects.md.
Values read from the Forever rank text (fixture build 1.60.1.70205); checked at max rank."""

from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.schema import EFFECT_KINDS
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
HUNTER = class_module("hunter")
RAW, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205-hunter"), HUNTER.LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "hunter.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
CLS, REPORT = attach_effects(RAW, HUNTER.TALENT_EFFECTS, HUNTER.UNMODELED)


def test_coverage_still_holds():
    assert REPORT == []


def test_new_effect_kinds_exist():
    assert {"ap_from_int_pct", "stat_pct"} <= EFFECT_KINDS


@pytest.mark.parametrize("talent, kind, last, applies_to", [
    ("Lethal Attacks", "crit_chance", 5, ("all",)),
    ("Careful Aim", "ap_from_int_pct", 100, ("all",)),
    ("Mortal Shots", "crit_damage_pct", 30, ("@ranged",)),
    ("Ranged Weapon Specialization", "damage_pct", 5, ("@ranged",)),
    ("Barrage", "damage_pct", 10, ("Multi-Shot", "Aimed Shot", "Volley")),
    ("Improved Arcane Shot", "cooldown", -1.5, ("Arcane Shot",)),
    ("Efficiency", "mana_cost_pct", -15, ("@shot", "@sting", "@melee")),
    ("Lone Wolf", "damage_pct", 20, ("@no_pet",)),
    ("Savage Strikes", "crit_chance", 4, ("@melee",)),
    ("Lacerating Strikes", "dot_pct", 40, ("Mongoose Bite",)),
    ("Improved Stings", "damage_pct", 20, ("Serpent Sting",)),
    ("Lightning Reflexes", "stat_pct", 10, ("agility",)),
    ("Surefooted", "hit_chance", 3, ("all",)),
    ("Improved Tracking", "damage_pct", 5, ("@tracked",)),
    ("Focused Fire", "damage_pct", 2, ("@with_pet",)),
    ("Unleashed Fury", "damage_pct", 15, ("@pet",)),
    ("Ferocity", "crit_chance", 10, ("@pet",)),
])
def test_rule_values_at_max_rank(talent, kind, last, applies_to):
    t = CLS.talent_named(talent)
    (e,) = [e for e in t.effects if e.kind == kind]
    assert len(e.values) == t.max_rank
    assert e.values[-1] == last and e.applies_to == applies_to


def test_predators_edge_has_two_rules():
    pe = CLS.talent_named("Predator's Edge")
    got = {(e.kind, e.applies_to): e.values[-1] for e in pe.effects}
    assert got == {("crit_damage_pct", ("@melee",)): 30, ("damage_pct", ("@off_hand",)): 50}
