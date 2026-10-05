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
TABLES = read_tables(FIX / "wago-1.60.1.70205-warrior")
PAGE = parse_page((FIX / "wowforevertalent" / "warrior.html").read_text(encoding="utf-8"))
RAW, NORMALIZED = normalize_class(TABLES, WARRIOR.LAYOUT, PAGE, wago_build="1.60.1.70205")
CLS, REPORT = attach_effects(RAW, WARRIOR.TALENT_EFFECTS, WARRIOR.UNMODELED)

CATEGORIES = ("melee damage", "rage", "defensive", "control", "mobility", "threat", "shout",
              "utility", "proc")

# The page (build 1.60.1.70170) predates the client tables (70205): Fury and Protection were
# reshuffled, so these talents have no rank text until wowforevertalent.com catches up.
NO_RANK_TEXT = {"Iron Will", "Improved Cleave", "Boundless Rage", "Precision", "Improved Berserker Rage",
                "Flurry", "Anticipation", "Improved Bloodrage", "Toughness", "Improved Revenge",
                "Improved Disarm", "Vanguard", "Improved Shield Bash", "Bastion", "Focused Rage"}


def test_warrior_is_registered_with_its_trait_tree_and_skill_lines():
    assert WARRIOR.LAYOUT.class_name == "warrior" and WARRIOR.LAYOUT.trait_tree_id == 1117
    assert WARRIOR.SKILL_LINES == (26, 256, 257)


def test_three_trees_load_with_every_talent():
    assert len(CLS.talents) == 53
    assert {t.name: len(t.talent_ids) for t in CLS.trees} == {"Arms": 17, "Fury": 18, "Protection": 18}
    names = {t.name for t in CLS.talents}
    assert {"Mortal Strike", "Bloodthirst", "Shield Slam", "Sweeping Strikes", "Death Wish",
            "Improved Hamstring", "Concussion Blow", "Spearing Strike"} <= names


def test_talents_without_rank_text_are_the_page_drift():
    assert {t.name for t in CLS.talents if not t.rank_text} == NO_RANK_TEXT
    assert "source builds disagree" in (NORMALIZED.build_mismatch or "")


def test_every_talent_is_classified_exactly_once():
    assert REPORT == []


def test_unmodeled_reasons_name_a_category():
    # "<category>: <what the talent does>", or "grants_spell"; talents without rank text say so
    for name, reason in WARRIOR.UNMODELED.items():
        if reason == "grants_spell":
            continue
        category, _, what = reason.partition(": ")
        assert category in CATEGORIES and what, (name, reason)
        assert reason.endswith("(no rank text)") == (name in NO_RANK_TEXT), (name, reason)


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
