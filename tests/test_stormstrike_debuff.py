"""Stormstrike's debuff (#398): +20% damage on the next Earth Shock within 12 s. With Stormstrike every 8 s and
Earth Shock every few seconds, the share of shocks that follow a Stormstrike is shock period / Stormstrike period
(at most 1)."""

import pytest

from wowforever.classes import class_module
from wowforever.classes.shaman_rotation import enhancement_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.physical import Target
from wowforever.scenarios import best_rank
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.toml_cache import load_toml

S = class_module("shaman")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("shaman"), S.TALENT_EFFECTS, S.UNMODELED)
STATS = stat_table("shaman").at(60).melee
STORM = {CLS.talent_named("Stormstrike").talent_id: 1}


def test_config_cites_the_data():
    from pathlib import Path

    cfg = load_toml(Path(__file__).resolve().parents[1] / "config" / "shaman.toml")["stormstrike"]
    assert cfg == {"bonus_pct": 20.0, "seconds": 12.0}


def test_earth_shock_share_by_hand():
    base = enhancement_rotation(STATS, CLS.spells, CLS, {}, Target(3, 0))
    storm = enhancement_rotation(STATS, CLS.spells, CLS, STORM, Target(3, 0))
    shock = best_rank(CLS.spells, "Earth Shock", 60)
    strike = best_rank(CLS.spells, "Stormstrike", 60)
    share = min(1.0, max(shock.cooldown, 1.5) / strike.cooldown)
    assert storm.spell_dps == pytest.approx(base.spell_dps * (1 + 0.20 * share))
