"""Rogue damage talents as effect rules (#131, part 2). Spec: docs/tasks/131-rogue-effects.md.
Values are read from the Forever rank text (fixture build 1.60.1.70205); checked at max rank."""

from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.schema import EFFECT_KINDS
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
ROGUE = class_module("rogue")
RAW, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205-rogue"), ROGUE.LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "rogue.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
CLS, REPORT = attach_effects(RAW, ROGUE.TALENT_EFFECTS, ROGUE.UNMODELED)


def effect(name, kind):
    t = CLS.talent_named(name)
    (e,) = [e for e in t.effects if e.kind == kind]
    assert len(e.values) == t.max_rank
    return e


def test_coverage_still_holds():
    assert REPORT == []


def test_new_effect_kinds_exist():
    assert {"energy_cost", "dodge_reduction", "armor_pen"} <= EFFECT_KINDS


@pytest.mark.parametrize("talent, kind, last, applies_to", [
    ("Malice", "crit_chance", 5, ("all",)),
    ("Lethality", "crit_damage_pct", 20, ("Sinister Strike", "Gouge", "Backstab", "Mutilate",
                                          "Ghostly Strike", "Hemorrhage")),
    ("Aggression", "damage_pct", 6, ("Sinister Strike", "Backstab", "Eviscerate")),
    ("Improved Eviscerate", "damage_pct", 20, ("Eviscerate",)),
    ("Dual Wield Specialization", "damage_pct", 25, ("@off_hand",)),
    ("Precision", "hit_chance", 3, ("all",)),
    ("Weapon Expertise", "dodge_reduction", 2, ("all",)),
    ("Opportunity", "damage_pct", 10, ("Backstab", "Garrote", "Ambush", "Mutilate")),
    ("Relentless Strikes", "resource", 20, ("@finisher",)),
    ("Ruthlessness", "proc_chance", 60, ("@finisher",)),
    ("Seal Fate", "proc_chance", 100, ("@builder_crit",)),
    ("Improved Sinister Strike", "energy_cost", -5, ("Sinister Strike",)),
    ("Improved Slice and Dice", "duration", 45, ("Slice and Dice",)),
    ("Vile Poisons", "damage_pct", 20, ("@poison",)),
    ("Murder", "damage_pct", 4, ("@humanoid",)),
    ("Serrated Blades", "armor_pen", 9, ("all",)),
    ("Improved Ambush", "crit_chance", 45, ("Ambush",)),
])
def test_rule_values_at_max_rank(talent, kind, last, applies_to):
    e = effect(talent, kind)
    assert e.values[-1] == last and e.applies_to == applies_to


def test_puncturing_wounds_has_crit_and_combo_point_effects():
    pw = CLS.talent_named("Puncturing Wounds")
    crits = {e.applies_to: e.values[-1] for e in pw.effects if e.kind == "crit_chance"}
    assert crits == {("Backstab",): 30, ("Mutilate",): 15}
    assert [e.values[-1] for e in pw.effects if e.kind == "proc_chance"] == [45]


def test_modeled_talents_left_unmodeled():
    modeled = {"Malice", "Lethality", "Aggression", "Improved Eviscerate", "Dual Wield Specialization",
               "Precision", "Weapon Expertise", "Opportunity", "Relentless Strikes", "Ruthlessness",
               "Seal Fate", "Puncturing Wounds", "Improved Sinister Strike", "Improved Slice and Dice",
               "Vile Poisons", "Murder", "Serrated Blades", "Improved Ambush"}
    assert modeled <= set(ROGUE.TALENT_EFFECTS) and not modeled & set(ROGUE.UNMODELED)
