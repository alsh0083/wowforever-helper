"""Talent data for the remaining opponent classes (#152, part of #34): each class's Forever trees
and spells load from the trimmed client tables (tools/make_fixtures.py), every talent is
classified, and its opponent kits use the client's numbers. Spec: docs/tasks/152-<class>.md."""

import tomllib
from pathlib import Path

import pytest

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells
from wowforever.sources.wowforevertalent import parse_page

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"

CATEGORIES = ("damage", "healing", "resource", "defensive", "control", "mobility", "threat", "pet",
              "buff", "form", "utility", "proc")

CLASSES = {
    # class: (trait tree, skill lines, talents per tree, talents that teach an ability)
    "druid": (1089, (574, 134, 573), {"Balance": 16, "Feral Combat": 20, "Restoration": 16},
              {"Moonkin Form", "Shifting Power", "Feral Charge", "Swiftmend", "Nature's Swiftness", "Wild Growth"}),
    "paladin": (1100, (594, 267, 184), {"Holy": 17, "Protection": 16, "Retribution": 17},
                {"Divine Favor", "Holy Shock", "Templar's Bulwark", "Seal of Command", "Repentance"}),
    "priest": (1114, (613, 56, 78), {"Discipline": 18, "Holy": 17, "Shadow": 18},
               {"Inner Focus", "Holy Nova", "Binding Heal", "Prayer of Mending", "Mind Flay", "Silence",
                "Vampiric Embrace", "Shadowform"}),
    "shaman": (1082, (375, 373, 374), {"Elemental": 16, "Enhancement": 18, "Restoration": 16},
               {"Stormstrike", "Water Shield", "Mana Tide Totem", "Nature's Swiftness", "Riptide"}),
    "warlock": (1116, (355, 354, 593), {"Affliction": 17, "Demonology": 19, "Destruction": 16},
                {"Curse of Exhaustion", "Demonic Sacrifice", "Shadowburn", "Incinerate"}),
}


def loaded(name):
    module = class_module(name)
    tables = read_tables(FIX / f"wago-1.60.1.70205-{name}")
    page = parse_page((FIX / "wowforevertalent" / f"{name}.html").read_text(encoding="utf-8"))
    raw, _ = normalize_class(tables, module.LAYOUT, page, wago_build="1.60.1.70205")
    cls, report = attach_effects(raw, module.TALENT_EFFECTS, module.UNMODELED)
    return module, tables, cls, report


@pytest.mark.parametrize("name", sorted(CLASSES))
def test_trees_load_with_every_talent_and_rank_text(name):
    tree, lines, counts, _ = CLASSES[name]
    module, _, cls, _ = loaded(name)
    assert module.LAYOUT.trait_tree_id == tree and module.SKILL_LINES == lines
    assert {t.name: len(t.talent_ids) for t in cls.trees} == counts
    assert all(t.rank_text for t in cls.talents)     # the page and the client agree for these classes


def test_off_grid_nodes_snap_or_hide():
    names = {n: [t.name for t in loaded(n)[2].talents] for n in ("paladin", "warlock", "priest")}
    assert {"Improved Seal of Fury", "Swift Judgement"} <= set(names["paladin"])
    assert {"Amplify Curse", "Improved Life Tap"} <= set(names["warlock"])
    # the parked node duplicates the Holy Specialization on the grid
    assert names["priest"].count("Holy Specialization") == 1


@pytest.mark.parametrize("name", sorted(CLASSES))
def test_every_talent_is_classified_exactly_once(name):
    assert loaded(name)[3] == []


@pytest.mark.parametrize("name", sorted(CLASSES))
def test_unmodeled_reasons_name_a_category(name):
    module = class_module(name)
    for talent, reason in module.UNMODELED.items():
        if reason == "grants_spell":
            continue
        category, _, what = reason.partition(": ")
        assert category in CATEGORIES and what, (talent, reason)


@pytest.mark.parametrize("name", sorted(CLASSES))
def test_talents_that_teach_an_ability_are_grants_spell(name):
    module = class_module(name)
    for talent in CLASSES[name][3]:
        # stage 2 classes move some of these into TALENT_EFFECTS (Shadowform, #164)
        assert module.UNMODELED.get(talent) == "grants_spell" or talent in module.TALENT_EFFECTS, talent


@pytest.mark.parametrize("name", sorted(CLASSES))
def test_kit_controls_from_data_match_the_spells(name):
    # controls whose source says "data" use the client's cooldown and duration
    module, tables, _, _ = loaded(name)
    spells = {s.name: s for s in class_spells(tables, skill_lines=module.SKILL_LINES)}
    kits = sorted((ROOT / "config" / "opponents").glob(f"{name}-*.toml"))
    assert kits
    for path in kits:
        for c in tomllib.loads(path.read_text(encoding="utf-8")).get("controls", []):
            if c.get("source", "").startswith("data"):
                s = spells[c["name"]]
                assert (s.cooldown, s.duration) == (c["cooldown"], c["duration"]), (path.stem, c["name"])
