"""Tests for revision tracking (#11): talent/spell diffs, changelog, build registry, affected builds."""

import json
from dataclasses import replace

from wowforever.builds import Build
from wowforever.revisions import (
    affected_builds, append_changelog, diff_class, diff_spells, record_check,
)
from wowforever.schema import ClassData, Prerequisite, SpellRank, Talent, Tree


def talent(tid, name, row, col, max_rank, text=(), prereq=None, tree=2):
    return Talent(tid, name, tree, row, col, max_rank, (), text, prereq)


IGNITE = talent(1, "Ignite", 1, 0, 5, tuple(f"{8 * r}%" for r in range(1, 6)))
IMPACT = talent(2, "Impact", 1, 2, 3, ("3%", "7%", "10%"))
PYRO = talent(3, "Pyroblast", 2, 2, 1, ("Pyro",))
HEAT = talent(4, "Heating Up", 3, 2, 1, ("Heat",), Prerequisite(3, 1))
OLD = ClassData("mage", (Tree(2, "Fire", (1, 2, 3, 4)),), (IGNITE, IMPACT, PYRO, HEAT))


def changed(*talents):
    return ClassData("mage", (Tree(2, "Fire", tuple(t.talent_id for t in talents)),), tuple(talents))


def lines(changes):
    return sorted(str(c) for c in changes)


def test_no_changes():
    assert diff_class(OLD, OLD) == []


def test_rank_count_and_text_changes_are_described():
    new = changed(IGNITE, replace(IMPACT, max_rank=2, rank_text=("5%", "10%")), PYRO, HEAT)
    assert lines(diff_class(OLD, new)) == [
        "Fire/Impact: max rank 3 -> 2",
        "Fire/Impact: rank text changed",
    ]


def test_move_is_described_with_rows_and_columns_1_indexed():
    new = changed(IGNITE, IMPACT, PYRO, replace(HEAT, row=4, col=1))
    assert lines(diff_class(OLD, new)) == ["Fire/Heating Up: moved from row 4 col 3 to row 5 col 2"]


def test_added_removed_renamed_and_prerequisite_changes():
    blast = talent(5, "Blast Wave", 4, 2, 1, ("Wave",))
    new = changed(IGNITE, replace(IMPACT, name="Improved Impact"), PYRO, replace(HEAT, prerequisite=None), blast)
    new_old_ignite_removed = changed(IMPACT, PYRO, HEAT)
    assert lines(diff_class(OLD, new)) == [
        "Fire/Blast Wave: new talent",
        "Fire/Heating Up: prerequisite Pyroblast (rank 1) -> none",
        "Fire/Impact: renamed to Improved Impact",
    ]
    assert lines(diff_class(OLD, new_old_ignite_removed)) == ["Fire/Ignite: removed"]


def test_change_records_talent_name_for_affected_build_lookup():
    new = changed(IGNITE, replace(IMPACT, max_rank=2), PYRO, HEAT)
    (c,) = diff_class(OLD, new)
    assert (c.talent, c.kind) == ("Impact", "changed")


def test_spell_diffs_by_spell_id():
    fb = SpellRank(133, "Fireball", 1, 1, ("fire",), 1.5, mana_cost=30, min_damage=14, max_damage=22)
    new = replace(fb, cast_time=2.0, min_damage=15)
    blizz = SpellRank(10, "Blizzard", 1, 20, ("frost",), 0.0)
    assert lines(diff_spells((fb,), (new, blizz))) == [
        "Blizzard rank 1: new spell rank",
        "Fireball rank 1: cast_time 1.5 -> 2.0",
        "Fireball rank 1: min_damage 14 -> 15",
    ]
    assert lines(diff_spells((fb, blizz), (fb,))) == ["Blizzard rank 1: removed"]


def test_affected_builds_are_those_naming_a_changed_talent():
    a = Build("a", "A", "", {"Impact": 3, "Ignite": 5})
    b = Build("b", "B", "", {"Ignite": 5}, must_have_by={"Pyroblast": 30})
    c = Build("c", "C", "", {"Ignite": 5})
    new = changed(IGNITE, replace(IMPACT, max_rank=2), replace(PYRO, row=3), HEAT)
    assert affected_builds(diff_class(OLD, new), [a, b, c]) == ["a", "b"]


def test_append_changelog_adds_a_dated_section_per_build(tmp_path):
    log = tmp_path / "CHANGELOG.md"
    new = changed(IGNITE, replace(IMPACT, max_rank=2), PYRO, HEAT)
    append_changelog(log, "1.60.1.70300", diff_class(OLD, new), date="2026-10-05")
    append_changelog(log, "1.60.1.70400", [], date="2026-10-06")
    text = log.read_text(encoding="utf-8")
    assert text.startswith("# Data changelog\n")
    assert "## 1.60.1.70300 (2026-10-05)\n\n- Fire/Impact: max rank 3 -> 2\n" in text
    assert "## 1.60.1.70400 (2026-10-06)\n\n- No talent or spell changes.\n" in text
    assert text.index("70400") < text.index("70300")              # newest first


def test_record_check_registry(tmp_path):
    reg = tmp_path / "builds.json"
    record_check(reg, "1.60.1.70205", changed=True, dataset="data/datasets/1.60.1.70205.json",
                 checked_at="2026-10-04T20:00:00Z")
    record_check(reg, "1.60.1.70300", changed=False, dataset=None, checked_at="2026-10-05T20:00:00Z")
    record_check(reg, "1.60.1.70300", changed=False, dataset=None, checked_at="2026-10-06T20:00:00Z")
    data = json.loads(reg.read_text(encoding="utf-8"))
    assert [e["build"] for e in data] == ["1.60.1.70205", "1.60.1.70300"]       # one entry per build
    assert data[1] == {"build": "1.60.1.70300", "changed": False, "dataset": None,
                       "checked_at": "2026-10-06T20:00:00Z"}                     # latest check wins
