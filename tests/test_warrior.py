"""Warrior talent data (#149, part of #34): the Forever warrior trees and spells load from the
trimmed client tables (tools/make_fixtures.py), and every talent is classified.
Spec: docs/tasks/149-warrior.md."""

from pathlib import Path

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
WARRIOR = class_module("warrior")
TABLES = read_tables(FIX / "wago-1.60.1.70291-warrior")
PAGE = parse_page((FIX / "wowforevertalent" / "warrior.html").read_text(encoding="utf-8"))
RAW, NORMALIZED = normalize_class(TABLES, WARRIOR.LAYOUT, PAGE, wago_build="1.60.1.70291")
CLS, REPORT = attach_effects(RAW, WARRIOR.TALENT_EFFECTS, WARRIOR.UNMODELED)

CATEGORIES = ("melee damage", "rage", "defensive", "control", "mobility", "threat", "shout",
              "utility", "proc")

# Build 1.60.1.70291 reworked Fury and Protection (#239); the page now has rank text for every talent.


def test_warrior_is_registered_with_its_trait_tree_and_skill_lines():
    assert WARRIOR.LAYOUT.class_name == "warrior" and WARRIOR.LAYOUT.trait_tree_id == 1117
    assert WARRIOR.SKILL_LINES == (26, 256, 257)


def test_three_trees_load_with_every_talent():
    assert len(CLS.talents) == 52
    assert {t.name: len(t.talent_ids) for t in CLS.trees} == {"Arms": 17, "Fury": 17, "Protection": 18}
    names = {t.name for t in CLS.talents}
    assert {"Mortal Strike", "Bloodthirst", "Shield Slam", "Sweeping Strikes", "Death Wish",
            "Improved Hamstring", "Concussion Blow", "Spearing Strike"} <= names


def test_every_talent_has_rank_text_after_the_rework():
    assert all(t.rank_text for t in CLS.talents)
    assert {"Lingering Rage", "Furious Precision", "Gore Drinker"} <= {t.name for t in CLS.talents}
    assert not {"Improved Cleave", "Precision", "Toughness", "Boundless Rage"} & {t.name for t in CLS.talents}
    assert "source builds disagree" in (NORMALIZED.build_mismatch or "")


def test_every_talent_is_classified_exactly_once():
    assert REPORT == []


def test_unmodeled_reasons_name_a_category():
    # "<category>: <what the talent does>", or "grants_spell"
    for name, reason in WARRIOR.UNMODELED.items():
        if reason == "grants_spell":
            continue
        category, _, what = reason.partition(": ")
        assert category in CATEGORIES and what, (name, reason)


def test_talents_that_teach_an_ability_are_grants_spell():
    for name in ("Mortal Strike", "Sweeping Strikes", "Spearing Strike", "Piercing Howl", "Death Wish",
                 "Bloodthirst", "Last Stand", "Concussion Blow", "Shield Slam"):
        assert WARRIOR.UNMODELED[name] == "grants_spell", name


def test_warrior_spells_load():
    spells = {s.name: s for s in class_spells(TABLES, skill_lines=WARRIOR.SKILL_LINES)}
    assert {"Heroic Strike", "Mortal Strike", "Hamstring", "Charge", "Intercept", "Pummel", "Shield Bash",
            "Intimidating Shout", "Disarm", "Berserker Rage", "Overpower", "Execute", "Whirlwind",
            "Rend", "Thunder Clap", "Piercing Howl"} <= set(spells)
    assert (spells["Charge"].cooldown, spells["Intercept"].cooldown, spells["Pummel"].cooldown) == (15, 30, 10)


def test_warrior_arms_kit_matches_the_spell_data():
    # the opponent kit (#34) uses the client's cooldowns and durations; Charge/Intercept stun
    # through triggered spells, so only their cooldowns are checked
    import tomllib

    kit = tomllib.loads((Path(__file__).parents[1] / "config" / "opponents" / "warrior-arms.toml")
                        .read_text(encoding="utf-8"))
    spells = {s.name: s for s in class_spells(TABLES, skill_lines=WARRIOR.SKILL_LINES)}
    for c in kit["controls"]:
        assert spells[c["name"]].cooldown == c["cooldown"], c["name"]
        if c["name"] not in ("Charge", "Intercept"):
            assert spells[c["name"]].duration == c["duration"], c["name"]


def test_every_warrior_talent_has_an_icon():
    # page icons by position, then by name for talents the site shows elsewhere, then the client's icon
    # file ids for the four the site lacks (ICON_OVERRIDES)
    cls, _ = normalize_class(TABLES, WARRIOR.LAYOUT, PAGE, wago_build="1.60.1.70291",
                             icon_overrides=WARRIOR.ICON_OVERRIDES)
    assert all(t.icon for t in cls.talents)
