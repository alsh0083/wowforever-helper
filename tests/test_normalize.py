"""Tests for the normalizer (#9) on real fixtures: wago.tools trait tables for build
1.60.1.70205 (mage trait tree 1112 only) and the wowforevertalent.com mage page (build 70170)."""

from dataclasses import replace
from pathlib import Path

import pytest

from wowforever.classes.mage import LAYOUT
from wowforever.normalize import normalize_class, read_tables
from wowforever.schema import Dataset, Provenance
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
TABLES = read_tables(FIX / "wago-1.60.1.70205")
PAGE = parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8"))
WAGO_BUILD = "1.60.1.70205"


@pytest.fixture(scope="module")
def result():
    return normalize_class(TABLES, LAYOUT, PAGE, wago_build=WAGO_BUILD)


def by_name(cls, name):
    return cls.talent_named(name)


def test_read_tables_loads_every_csv_as_rows_of_strings():
    assert set(TABLES) >= {"TraitNode", "TraitNodeEntry", "TraitNodeXTraitNodeEntry", "TraitDefinition",
                           "TraitEdge", "SpellName"}
    assert TABLES["TraitNode"][0]["TraitTreeID"] == "1112"


def test_trees_and_talent_counts(result):
    cls, _ = result
    assert cls.class_name == "mage"
    assert [(t.tree_id, t.name, len(t.talent_ids)) for t in cls.trees] == [
        (1, "Arcane", 18), (2, "Fire", 17), (3, "Frost", 19)]
    assert len(cls.talents) == 54


def test_tree_talents_ordered_by_row_then_column(result):
    cls, _ = result
    fire = cls.trees[1]
    positions = [(cls.talent(t).row, cls.talent(t).col) for t in fire.talent_ids]
    assert positions == sorted(positions)


def test_positions_ranks_and_identity_from_trait_tables(result):
    cls, _ = result
    ignite = by_name(cls, "Ignite")
    assert (ignite.talent_id, ignite.tree_id, ignite.row, ignite.col, ignite.max_rank) == (105794, 2, 1, 0, 5)
    wake = by_name(cls, "Wake of Fire")
    assert (wake.row, wake.col, wake.max_rank) == (0, 0, 2)
    assert by_name(cls, "Arcane Power").row == 6
    assert ignite.spell_id > 0
    assert ignite.rank_spell_ids == ()


def test_prerequisites_from_trait_edges_require_full_rank(result):
    cls, _ = result
    pairs = {(cls.talent(t.prerequisite.talent_id).name, t.name, t.prerequisite.rank)
             for t in cls.talents if t.prerequisite}
    assert pairs == {
        ("Ice Lance", "Fingers of Frost", 1),
        ("Cold Snap", "Ice Barrier", 1),
        ("Critical Mass", "Combustion", 3),
        ("Arcane Concentration", "Arcane Meditation", 5),
        ("Presence of Mind", "Arcane Power", 1),
        ("Pyroblast", "Heating Up", 1),
    }


def test_rank_text_classic_status_and_icon_from_wowforevertalent(result):
    cls, _ = result
    ignite = by_name(cls, "Ignite")
    assert len(ignite.rank_text) == 5 and "40%" in ignite.rank_text[4]
    assert ignite.classic_status == "same"
    assert ignite.icon == "spell_fire_incinerate"
    assert by_name(cls, "Ice Lance").classic_status == "new"
    assert by_name(cls, "Ice Block").classic_status == "moved"


def test_result_validates_as_a_dataset(result):
    cls, _ = result
    prov = Provenance("wago.tools", WAGO_BUILD, WAGO_BUILD, "2026-10-04T00:00:00Z", "0" * 64)
    Dataset(WAGO_BUILD, WAGO_BUILD, (cls,), (prov,)).validate()


def test_report_flags_source_build_lag_and_nothing_else(result):
    _, report = result
    assert report.build_mismatch is not None
    assert "1.60.1.70170" in report.build_mismatch and "1.60.1.70205" in report.build_mismatch
    assert report.unmatched_wago == []
    assert report.unmatched_wft == []
    assert report.name_mismatches == []
    assert not report.ok


def test_report_ok_when_builds_agree():
    _, report = normalize_class(TABLES, LAYOUT, replace(PAGE, game_build=WAGO_BUILD), wago_build=WAGO_BUILD)
    assert report.build_mismatch is None and report.ok


def test_talent_missing_from_wowforevertalent_is_kept_and_reported():
    trees = [dict(t) for t in PAGE.trees]
    trees[1] = {**trees[1], "talents": [t for t in trees[1]["talents"] if t["name"] != "Ignite"]}
    cls, report = normalize_class(TABLES, LAYOUT, replace(PAGE, trees=trees), wago_build=WAGO_BUILD)
    ignite = by_name(cls, "Ignite")
    assert ignite.rank_text == () and ignite.classic_status is None
    assert any("Ignite" in u for u in report.unmatched_wago)


def test_name_mismatch_at_same_position_is_reported_and_text_not_attached():
    trees = [dict(t) for t in PAGE.trees]
    fire = [dict(t) for t in trees[1]["talents"]]
    for t in fire:
        if t["name"] == "Ignite":
            t["name"] = "Ignyte"
    trees[1] = {**trees[1], "talents": fire}
    cls, report = normalize_class(TABLES, LAYOUT, replace(PAGE, trees=trees), wago_build=WAGO_BUILD)
    assert by_name(cls, "Ignite").rank_text == ()
    assert any("Ignite" in m and "Ignyte" in m for m in report.name_mismatches)
