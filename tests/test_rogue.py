"""Rogue talent data (#103, part 2): the Forever rogue trees and spells load from the trimmed
client tables (tools/make_fixtures.py), and every talent is classified. Spec: docs/tasks/103-rogue.md."""

from pathlib import Path

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
ROGUE = class_module("rogue")
TABLES = read_tables(FIX / "wago-1.60.1.70205-rogue")
PAGE = parse_page((FIX / "wowforevertalent" / "rogue.html").read_text(encoding="utf-8"))
RAW, _ = normalize_class(TABLES, ROGUE.LAYOUT, PAGE, wago_build="1.60.1.70205")
CLS, REPORT = attach_effects(RAW, ROGUE.TALENT_EFFECTS, ROGUE.UNMODELED)

CATEGORIES = ("melee damage", "resource", "defensive", "control", "stealth", "mobility", "utility",
              "poison", "proc")


def test_rogue_is_registered_with_its_trait_tree_and_skill_lines():
    assert ROGUE.LAYOUT.class_name == "rogue" and ROGUE.LAYOUT.trait_tree_id == 1111
    assert ROGUE.SKILL_LINES == (253, 38, 39, 40)


def test_three_trees_load_with_every_talent():
    assert len(CLS.talents) == 53
    assert {t.name: len(t.talent_ids) for t in CLS.trees} == {
        "Assassination": 17, "Combat": 17, "Subtlety": 19}
    names = {t.name for t in CLS.talents}
    assert {"Mutilate", "Seal Fate", "Adrenaline Rush", "Blade Flurry", "Preparation",
            "Premeditation", "Hemorrhage", "Improved Sprint"} <= names


def test_every_talent_is_classified_exactly_once():
    assert REPORT == []


def test_unmodeled_reasons_name_a_category():
    # "<category>: <what the talent does>", or "grants_spell"; melee damage points at #111
    for name, reason in ROGUE.UNMODELED.items():
        if reason == "grants_spell":
            continue
        category, _, what = reason.partition(": ")
        assert category in CATEGORIES and what, (name, reason)
        if category == "melee damage":
            assert reason.endswith("(#111)"), (name, reason)


def test_talents_that_teach_an_ability_are_grants_spell():
    for name in ("Mutilate", "Adrenaline Rush", "Blade Flurry", "Preparation", "Premeditation",
                 "Hemorrhage", "Cold Blood", "Ghostly Strike", "Riposte"):
        assert ROGUE.UNMODELED[name] == "grants_spell", name


def test_rogue_spells_load():
    spells = class_spells(TABLES, skill_lines=ROGUE.SKILL_LINES)
    names = {s.name for s in spells}
    assert {"Sinister Strike", "Eviscerate", "Backstab", "Kidney Shot", "Cheap Shot", "Gouge",
            "Blind", "Vanish", "Sprint", "Evasion", "Kick", "Sap"} <= names
