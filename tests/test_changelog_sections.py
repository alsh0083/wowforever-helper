"""Tests for #241: one changelog section per build, date and note, however many classes an update checks."""

from pathlib import Path

from wowforever.revisions import Change, append_changelog, collapse_changelog

HEADER = "# Data changelog\n"
NO_CHANGES = "- No talent or spell changes.\n"
NOTE = "> Not a game change: same build, but the tool started recording energy costs.\n"


def change(scope, talent, text):
    return Change(scope, talent, "changed", text)


def test_same_build_and_date_merges_into_one_section(tmp_path):
    log = tmp_path / "CHANGELOG.md"
    append_changelog(log, "1.60.1.70291", [change("Fury", "Flurry", "prerequisite Bloodthirst -> Death Wish")],
                     date="2026-10-09")
    append_changelog(log, "1.60.1.70291", [change("Arms", "Impale", "prerequisite none -> Deep Wounds (rank 3)")],
                     date="2026-10-09")
    text = log.read_text(encoding="utf-8")
    assert text.count("## 1.60.1.70291") == 1
    lines = [line for line in text.splitlines() if line.startswith("- ")]
    assert lines == sorted(lines) and len(lines) == 2                  # merged lines stay sorted


def test_merging_drops_no_changes_and_duplicates(tmp_path):
    log = tmp_path / "CHANGELOG.md"
    impale = change("Arms", "Impale", "prerequisite none -> Deep Wounds (rank 3)")
    append_changelog(log, "1.60.1.70291", [], date="2026-10-09")
    append_changelog(log, "1.60.1.70291", [impale], date="2026-10-09")
    append_changelog(log, "1.60.1.70291", [impale], date="2026-10-09")
    append_changelog(log, "1.60.1.70291", [], date="2026-10-09")
    assert log.read_text(encoding="utf-8") == HEADER + f"\n## 1.60.1.70291 (2026-10-09)\n\n- {impale}\n"


def test_only_no_changes_stays_a_single_line(tmp_path):
    log = tmp_path / "CHANGELOG.md"
    for _ in range(3):
        append_changelog(log, "1.60.1.70338", [], date="2026-10-10")
    assert log.read_text(encoding="utf-8") == HEADER + "\n## 1.60.1.70338 (2026-10-10)\n\n" + NO_CHANGES


def test_new_date_or_build_starts_a_new_section(tmp_path):
    log = tmp_path / "CHANGELOG.md"
    append_changelog(log, "1.60.1.70291", [], date="2026-10-09")
    append_changelog(log, "1.60.1.70291", [], date="2026-10-10")
    append_changelog(log, "1.60.1.70338", [], date="2026-10-10")
    text = log.read_text(encoding="utf-8")
    assert text.count("## ") == 3
    assert text.index("70338 (2026-10-10)") < text.index("70291 (2026-10-10)") < text.index("70291 (2026-10-09)")


def test_annotated_newest_section_is_not_merged_into(tmp_path):
    # a hand-written note describes only its own lines, so new lines get their own section
    log = tmp_path / "CHANGELOG.md"
    log.write_text(HEADER + "\n## 1.60.1.70205 (2026-10-05)\n\n" + NOTE + "\n- Venom rank 1: energy_cost 0 -> 25\n",
                   encoding="utf-8")
    append_changelog(log, "1.60.1.70205", [], date="2026-10-05")
    text = log.read_text(encoding="utf-8")
    assert text == (HEADER + "\n## 1.60.1.70205 (2026-10-05)\n\n" + NO_CHANGES
                    + "\n## 1.60.1.70205 (2026-10-05)\n\n" + NOTE + "\n- Venom rank 1: energy_cost 0 -> 25\n")


def test_collapse_merges_sections_with_the_same_heading_and_note():
    text = (HEADER
            + "\n## 1.60.1.70291 (2026-10-09)\n\n- b\n- d\n"
            + "\n## 1.60.1.70291 (2026-10-09)\n\n- a\n- b\n"
            + "\n## 1.60.1.70205 (2026-10-05)\n\n" + NOTE + "\n- x\n"
            + "\n## 1.60.1.70205 (2026-10-05)\n\n- hunter/(class): class added\n"
            + "\n## 1.60.1.70205 (2026-10-05)\n\n" + NOTE + "\n- w\n"
            + "\n## 1.60.1.70205 (2026-10-05)\n\n" + NO_CHANGES
            + "\n## 1.60.1.70205 (2026-10-05)\n\n- rogue/(class): class added\n")
    # each merged section sits where its first occurrence was; lines sorted, unique, "no changes" dropped
    assert collapse_changelog(text) == (
        HEADER
        + "\n## 1.60.1.70291 (2026-10-09)\n\n- a\n- b\n- d\n"
        + "\n## 1.60.1.70205 (2026-10-05)\n\n" + NOTE + "\n- w\n- x\n"
        + "\n## 1.60.1.70205 (2026-10-05)\n\n- hunter/(class): class added\n- rogue/(class): class added\n")


def test_collapse_keeps_a_section_of_only_no_changes():
    text = HEADER + "\n## 1.60.1.70338 (2026-10-10)\n\n" + NO_CHANGES + "\n## 1.60.1.70338 (2026-10-10)\n\n" + NO_CHANGES
    assert collapse_changelog(text) == HEADER + "\n## 1.60.1.70338 (2026-10-10)\n\n" + NO_CHANGES


def test_collapse_is_idempotent_and_keeps_an_empty_changelog():
    assert collapse_changelog(HEADER) == HEADER
    text = HEADER + "\n## 1.60.1.70291 (2026-10-09)\n\n- a\n"
    assert collapse_changelog(collapse_changelog(text)) == text


def test_repo_changelog_is_collapsed():
    text = (Path(__file__).resolve().parent.parent / "data" / "CHANGELOG.md").read_text(encoding="utf-8")
    assert collapse_changelog(text) == text


def test_text_before_the_first_section_is_an_error_not_dropped():
    import pytest

    with pytest.raises(ValueError):
        collapse_changelog(HEADER + "\nA hand-written paragraph.\n\n## 1.60.1.70291 (2026-10-09)\n\n- a\n")
