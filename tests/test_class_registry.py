"""Multi-class infrastructure (#103, part 1): class registry, per-class builds, and merging a
class into a build's dataset. The mage path must stay exactly as before."""

import dataclasses
from pathlib import Path

import pytest

from wowforever.builds import Build, load_builds
from wowforever.classes import CLASSES, class_module
from wowforever.classes import mage
from wowforever.schema import Dataset, Provenance
from wowforever.update import merge_class

DATASET = Path(__file__).resolve().parents[1] / "data" / "datasets" / "1.60.1.70205.json"


def test_registry_maps_names_to_class_modules():
    assert "mage" in CLASSES
    m = class_module("mage")
    assert m is mage
    for attr in ("LAYOUT", "TALENT_EFFECTS", "UNMODELED", "SKILL_LINES"):
        assert hasattr(m, attr)
    with pytest.raises(KeyError):
        class_module("murloc")


def test_builds_carry_a_class_and_filter_by_it():
    builds = load_builds()
    mage, rogue = load_builds(class_name="mage"), load_builds(class_name="rogue")
    assert mage and rogue and len(mage) + len(rogue) <= len(builds)
    assert all(b.class_name == "mage" for b in mage) and all(b.class_name == "rogue" for b in rogue)
    assert {b.class_name for b in builds} <= set(CLASSES)


def test_build_class_is_read_from_toml(tmp_path):
    (tmp_path / "x.toml").write_text('id = "x"\nclass = "rogue"\nname = "X"\nsummary = "s"\n'
                                     '[final]\n"Malice" = 5\n', encoding="utf-8")
    (b,) = load_builds(tmp_path)
    assert b.class_name == "rogue"
    assert load_builds(tmp_path, class_name="mage") == []


def test_merge_class_adds_a_new_class_and_replaces_an_existing_one():
    ds = Dataset.load(DATASET)
    mage_cls = ds.class_data("mage")
    rogue = dataclasses.replace(mage_cls, class_name="rogue")
    extra = Provenance(source="wowforevertalent.com", game_build="x", data_version="rogue-page",
                       fetched_at="2026-10-05T00:00:00Z", snapshot_sha256="00")

    merged = merge_class(ds, rogue, (extra,))
    assert [c.class_name for c in merged.classes] == ["mage", "rogue"]
    assert extra in merged.provenance and set(ds.provenance) <= set(merged.provenance)

    again = merge_class(merged, dataclasses.replace(rogue, talents=rogue.talents[:3]), (extra,))
    assert [c.class_name for c in again.classes] == ["mage", "rogue"]
    assert len(again.class_data("rogue").talents) == 3
    assert again.provenance.count(extra) == 1          # provenance is not duplicated
