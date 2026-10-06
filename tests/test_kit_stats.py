"""Rogue, hunter and warrior opponent kits take level-60 health and DPS vs cloth from the melee engine (#147)."""

import tomllib
from pathlib import Path

import pytest

from wowforever.pvp.kit_stats import KIT_BUILDS, engine_at_60

ROOT = Path(__file__).resolve().parents[1]


def test_every_rogue_and_hunter_kit_has_a_build():
    kits = {p.stem for p in (ROOT / "config" / "opponents").glob("*.toml")
            if p.stem.startswith(tuple(f"{c}-" for c in {k.split("-")[0] for k in KIT_BUILDS}))}
    assert set(KIT_BUILDS) == kits
    builds = {p.stem for p in (ROOT / "config" / "builds").glob("*.toml")}
    assert set(KIT_BUILDS.values()) <= builds


@pytest.mark.parametrize("kit_id", sorted(KIT_BUILDS))
def test_kit_matches_the_engine(kit_id):
    health, dps = engine_at_60(kit_id)
    kit = tomllib.loads((ROOT / "config" / "opponents" / f"{kit_id}.toml").read_text(encoding="utf-8"))
    assert kit["at_60"]["health"] == pytest.approx(health, abs=1)
    assert kit["at_60"]["dps"] == pytest.approx(dps, abs=1)


def test_engine_values_are_plausible():
    health, dps = engine_at_60("rogue-combat")
    assert 2500 < health < 4500 and 150 < dps < 400
    # Subtlety's PvP build gives up damage for control
    assert engine_at_60("rogue-subtlety")[1] < dps
