"""Hunter talent data (#107): the Forever hunter trees and spells load from the trimmed
client tables (tools/make_fixtures.py), and every talent is classified. Spec: docs/tasks/107-hunter.md."""

from pathlib import Path

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
HUNTER = class_module("hunter")
TABLES = read_tables(FIX / "wago-1.60.1.70205-hunter")
PAGE = parse_page((FIX / "wowforevertalent" / "hunter.html").read_text(encoding="utf-8"))
RAW, _ = normalize_class(TABLES, HUNTER.LAYOUT, PAGE, wago_build="1.60.1.70205")
CLS, REPORT = attach_effects(RAW, HUNTER.TALENT_EFFECTS, HUNTER.UNMODELED)

CATEGORIES = ("ranged damage", "melee damage", "pet", "resource", "defensive", "control",
              "trap", "mobility", "utility", "proc")


def test_hunter_is_registered_with_its_trait_tree_and_skill_lines():
    assert HUNTER.LAYOUT.class_name == "hunter" and HUNTER.LAYOUT.trait_tree_id == 1091
    assert HUNTER.SKILL_LINES == (50, 163, 51)
    assert HUNTER.LAYOUT.hidden_nodes == frozenset({104982, 105003})   # parked Classic nodes


def test_three_trees_load_with_every_talent():
    assert len(CLS.talents) == 50
    assert {t.name: len(t.talent_ids) for t in CLS.trees} == {
        "Beast Mastery": 16, "Marksmanship": 16, "Survival": 18}
    names = {t.name for t in CLS.talents}
    assert {"Lone Wolf", "Bestial Wrath", "Intimidation", "Trueshot Aura", "Sniper Shot",
            "Strider Kick", "Lacerating Strikes", "Lightning Reflexes"} <= names
    assert CLS.talent_named("Bestial Wrath").prerequisite.talent_id == CLS.talent_named("Intimidation").talent_id


def test_every_talent_is_classified_exactly_once():
    assert REPORT == []


def test_unmodeled_reasons_name_a_category():
    # "<category>: <what the talent does>", or "grants_spell"; damage categories point at #111
    for name, reason in HUNTER.UNMODELED.items():
        if reason == "grants_spell":
            continue
        category, _, what = reason.partition(": ")
        assert category in CATEGORIES and what, (name, reason)
        if category in ("ranged damage", "melee damage", "pet"):
            assert reason.endswith("(#111)"), (name, reason)


def test_talents_that_teach_an_ability_are_grants_spell():
    for name in ("Bestial Wrath", "Intimidation", "Trueshot Aura", "Sniper Shot", "Strider Kick",
                 "Scatter Shot", "Deterrence", "Counterattack", "Summon Hawk"):
        assert HUNTER.UNMODELED[name] == "grants_spell", name


def test_hunter_spells_load():
    spells = class_spells(TABLES, skill_lines=HUNTER.SKILL_LINES)
    names = {s.name for s in spells}
    assert {"Auto Shot", "Arcane Shot", "Multi-Shot", "Aimed Shot", "Serpent Sting", "Concussive Shot",
            "Freezing Trap", "Feign Death", "Disengage", "Raptor Strike", "Wing Clip", "Rapid Fire"} <= names


def test_weapon_timed_shots_load_as_instant():
    # SpellCastTimes index 18 (base -1000000 ms) marks shots timed by the ranged weapon (#108)
    spells = {(s.name, s.rank): s for s in class_spells(TABLES, skill_lines=HUNTER.SKILL_LINES)}
    assert spells[("Arcane Shot", 1)].cast_time == 0.0
    assert all(s.cast_time >= 0 for s in spells.values())
