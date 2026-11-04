"""Level-60 health and sustained DPS vs cloth for the rogue and hunter opponent kits (#147).

The kits in config/opponents/ carried hand estimates for [at_60] health and DPS. The melee
engine (#111) computes them now: each kit maps to a community build, and the build's level-60
rotation against a cloth target (armor from config/pvp_self.toml) gives the DPS, with health
from the level-60 gear stats (config/stats/<class>.csv).
"""

from __future__ import annotations

import functools
from pathlib import Path

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.classes import engine
from wowforever.melee_scenarios import build_stats, stat_table
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.toml_cache import load_toml

ROOT = Path(__file__).resolve().parents[3]
DATASET = latest_dataset_path()

# kit id (config/opponents/<kit>.toml) -> community build id (config/builds/<build>.toml)
# Each kit plays its tree's build (#463): build ids change whenever the standards are re-imported (#460), trees don't.
KIT_TREES: dict[str, str] = {
    "rogue-combat": "Combat",
    "rogue-subtlety": "Subtlety",
    "hunter-marksmanship": "Marksmanship",
    "hunter-survival": "Survival",
    "warrior-arms": "Arms",
    "priest-shadow": "Shadow",
    "priest-discipline": "Discipline",
    "warlock-affliction": "Affliction",
    "warlock-destruction": "Destruction",
    "druid-balance": "Balance",
    "shaman-elemental": "Elemental",
    "paladin-retribution": "Retribution",
    "druid-feral": "Feral Combat",
    "shaman-enhancement": "Enhancement",
}


def kit_build(kit_id: str, cls):
    """The build a kit plays: of the class's endgame builds with the most points in the kit's tree, the PvP one
    before the PvE one and a community standard before a model build (ties: the lowest id)."""
    tree = next(tree for tree in cls.trees if tree.name == KIT_TREES[kit_id])
    names = {t.name for t in cls.talents}

    def main_tree(build):
        if not set(build.final) <= names:
            return None
        ids = build.final_ids(cls)
        return max(cls.trees, key=lambda tr: (sum(ids.get(t, 0) for t in tr.talent_ids), -tr.tree_id)).name

    mine = [b for b in load_builds(class_name=kit_id.split("-", 1)[0])
            if b.mode != "leveling" and main_tree(b) == tree.name]
    if not mine:
        raise KeyError(f"{kit_id}: no {tree.name} build in config/builds")
    return min(mine, key=lambda b: (b.variant != "PvP", b.origin != "community", b.id))


def engine_at_60(kit_id: str) -> tuple[float, float]:
    """Level-60 (health, sustained DPS vs cloth) for one kit, from the melee engine."""
    class_name = kit_id.split("-", 1)[0]
    m = class_module(class_name)
    cls, _ = attach_effects(Dataset.load(DATASET).class_data(class_name), m.TALENT_EFFECTS, m.UNMODELED)
    stats = stat_table(class_name).at(60)
    build = kit_build(kit_id, cls)
    ranks = build.final_ids(cls)
    cloth_armor = load_toml(ROOT / "config" / "pvp_self.toml")["cloth_armor"]
    dps = engine(class_name).output(stats, cls.spells, cls, ranks, Target(0, cloth_armor)).dps
    return build_stats(class_name, stats, cls, ranks).health, dps


def kit_ranks_at(build, cls, level: int) -> dict[int, int]:
    """The build's talent ranks at `level`: its first level - 9 points (the first comes at 10), in the
    build's order, or, without one, its final talents filled lowest tree row first (then talent id)."""
    points = max(0, level - 9)
    order = build.order_ids(cls)
    if order is None:
        final = build.final_ids(cls)
        row = {t.talent_id: t.row for t in cls.talents}
        order = [tid for tid in sorted(final, key=lambda t: (row[t], t)) for _ in range(final[tid])]
    ranks: dict[int, int] = {}
    for tid in order[:points]:
        ranks[tid] = ranks.get(tid, 0) + 1
    return ranks


@functools.lru_cache(maxsize=None)
def engine_at(kit_id: str, level: int) -> tuple[float, float]:
    """(health, sustained DPS vs cloth) for one kit at `level`, from the damage engine (#272)."""
    class_name = kit_id.split("-", 1)[0]
    m = class_module(class_name)
    cls, _ = attach_effects(Dataset.load(DATASET).class_data(class_name), m.TALENT_EFFECTS, m.UNMODELED)
    stats = stat_table(class_name).at(level)
    build = kit_build(kit_id, cls)
    ranks = kit_ranks_at(build, cls, level)
    cloth_armor = load_toml(ROOT / "config" / "pvp_self.toml")["cloth_armor"]
    dps = engine(class_name).output(stats, cls.spells, cls, ranks, Target(0, cloth_armor)).dps
    return build_stats(class_name, stats, cls, ranks).health, dps
