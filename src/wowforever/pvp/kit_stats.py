"""Level-60 health and sustained DPS vs cloth for the rogue and hunter opponent kits (#147).

The kits in config/opponents/ carried hand estimates for [at_60] health and DPS. The melee
engine (#111) computes them now: each kit maps to a community build, and the build's level-60
rotation against a cloth target (armor from config/pvp_self.toml) gives the DPS, with health
from the level-60 gear stats (config/stats/<class>.csv).
"""

from __future__ import annotations

from pathlib import Path

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import build_stats, rotation_output, stat_table
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.toml_cache import load_toml

ROOT = Path(__file__).resolve().parents[3]
DATASET = latest_dataset_path()

# kit id (config/opponents/<kit>.toml) -> community build id (config/builds/<build>.toml)
KIT_BUILDS: dict[str, str] = {
    "rogue-combat": "rogue-combat-pvp",
    "rogue-subtlety": "rogue-subtlety",
    "hunter-marksmanship": "hunter-marksmanship",
    "hunter-survival": "hunter-survival-pvp",
    "warrior-arms": "warrior-arms",
    "priest-shadow": "priest-shadow",
    "priest-discipline": "priest-discipline-smite",
    "warlock-affliction": "warlock-affliction",
    "warlock-destruction": "warlock-destruction",
    "druid-balance": "druid-balance",
    "shaman-elemental": "shaman-elemental",
    "paladin-retribution": "paladin-retribution-pvp",
    "druid-feral": "druid-feral",
    "shaman-enhancement": "shaman-enhancement",
}


def engine_at_60(kit_id: str) -> tuple[float, float]:
    """Level-60 (health, sustained DPS vs cloth) for one kit, from the melee engine."""
    class_name = kit_id.split("-", 1)[0]
    m = class_module(class_name)
    cls, _ = attach_effects(Dataset.load(DATASET).class_data(class_name), m.TALENT_EFFECTS, m.UNMODELED)
    stats = stat_table(class_name).at(60)
    build = {b.id: b for b in load_builds(class_name=class_name)}[KIT_BUILDS[kit_id]]
    ranks = build.final_ids(cls)
    cloth_armor = load_toml(ROOT / "config" / "pvp_self.toml")["cloth_armor"]
    dps = rotation_output(class_name, stats, cls.spells, cls, ranks, Target(0, cloth_armor)).dps
    return build_stats(class_name, stats, cls, ranks).health, dps
