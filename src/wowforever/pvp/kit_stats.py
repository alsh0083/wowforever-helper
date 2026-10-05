"""Level-60 health and sustained DPS vs cloth for the rogue and hunter opponent kits (#147).

The kits in config/opponents/ carried hand estimates for [at_60] health and DPS. The melee
engine (#111) computes them now: each kit maps to a community build, and the build's level-60
rotation against a cloth target (armor from config/pvp_self.toml) gives the DPS, with health
from the level-60 gear stats (config/stats/<class>.csv).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable, rotation_output
from wowforever.physical import Target
from wowforever.schema import Dataset

ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / "data" / "datasets" / "1.60.1.70205.json"

# kit id (config/opponents/<kit>.toml) -> community build id (config/builds/<build>.toml)
KIT_BUILDS: dict[str, str] = {
    "rogue-combat": "rogue-combat-pvp",
    "rogue-subtlety": "rogue-subtlety",
    "hunter-marksmanship": "hunter-marksmanship",
    "hunter-survival": "hunter-survival-pvp",
}


def engine_at_60(kit_id: str) -> tuple[float, float]:
    """Level-60 (health, sustained DPS vs cloth) for one kit, from the melee engine."""
    class_name = kit_id.split("-", 1)[0]
    m = class_module(class_name)
    cls, _ = attach_effects(Dataset.load(DATASET).class_data(class_name), m.TALENT_EFFECTS, m.UNMODELED)
    stats = MeleeStatTable.load(class_name).at(60)
    build = {b.id: b for b in load_builds(class_name=class_name)}[KIT_BUILDS[kit_id]]
    ranks = build.final_ids(cls)
    cloth_armor = tomllib.loads((ROOT / "config" / "pvp_self.toml").read_text(encoding="utf-8"))["cloth_armor"]
    dps = rotation_output(class_name, stats, cls.spells, cls, ranks, Target(60, cloth_armor)).dps
    return stats.health, dps
