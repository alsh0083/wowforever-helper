"""Rogue, hunter and warrior opponent kits take level-60 health and DPS vs cloth from the melee engine (#147)."""

import tomllib
from pathlib import Path

import pytest

from wowforever.pvp.kit_stats import KIT_TREES, engine_at_60, kit_build
from wowforever.schema import Dataset, latest_dataset_path

ROOT = Path(__file__).resolve().parents[1]
DS = Dataset.load(latest_dataset_path())


@pytest.mark.parametrize("kit_id", sorted(KIT_TREES))
def test_every_kit_plays_an_endgame_build_of_its_tree(kit_id):
    # build ids change when the standards are re-imported (#460); a kit follows its tree (#463)
    assert kit_id in {p.stem for p in (ROOT / "config" / "opponents").glob("*.toml")}
    cls = DS.class_data(kit_id.split("-", 1)[0])
    build = kit_build(kit_id, cls)
    ids = build.final_ids(cls)
    main = max(cls.trees, key=lambda tr: (sum(ids.get(t, 0) for t in tr.talent_ids), -tr.tree_id))
    assert main.name == KIT_TREES[kit_id] and build.mode != "leveling"


@pytest.mark.parametrize("kit_id", sorted(KIT_TREES))
def test_kit_matches_the_engine(kit_id):
    health, dps = engine_at_60(kit_id)
    kit = tomllib.loads((ROOT / "config" / "opponents" / f"{kit_id}.toml").read_text(encoding="utf-8"))
    assert kit["at_60"]["health"] == pytest.approx(health, abs=1)
    assert kit["at_60"]["dps"] == pytest.approx(dps, abs=1)


def test_engine_values_are_plausible():
    health, dps = engine_at_60("rogue-combat")
    assert 2500 < health < 4500 and 150 < dps < 450          # Shank lifts the rogue ~25% (#470)
    # Subtlety's PvP build gives up damage for control
    assert engine_at_60("rogue-subtlety")[1] < dps
