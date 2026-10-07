"""PvE scenarios for rogue and hunter (#133): questing kills/hour, dungeon-pull DPS and sustained raid
DPS, built on their rotations (#131, #132). Constants: config/melee_scenarios.toml, plus the mage's
questing anchors (mob HP, drink rates, travel) and raid mana budget from config/scenarios.toml.

Downtime: rogues and warriors eat back the health a fight costs them; hunters drink back the mana. Hunters
with a pet let it tank; a Lone Wolf hunter's health isn't modeled yet.
"""

from __future__ import annotations

import csv
import math
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from wowforever.melee_stats import MeleeStats
from wowforever.physical import Target
from wowforever.scenarios import _anchor_at, default_params
from wowforever.schema import ClassData, SpellRank

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "melee_scenarios.toml"
STATS_DIR = ROOT / "config" / "stats"
WEAPON_COLUMNS = {"main_hand": "mh", "off_hand": "oh", "ranged": "ranged"}


class MeleeStatTable:
    """config/stats/<class>.csv rows (from `gear-stats --class`), interpolated by level."""

    def __init__(self, rows: list[dict[str, float]]):
        self.rows = sorted(rows, key=lambda r: r["level"])

    @classmethod
    def load(cls, class_name: str, config_dir: Path = STATS_DIR) -> MeleeStatTable:
        with open(config_dir / f"{class_name}.csv", newline="", encoding="utf-8") as handle:
            return cls([{k: float(v) for k, v in row.items()} for row in csv.DictReader(handle)])

    def at(self, level: int) -> MeleeStats:
        lo, hi = self.rows[0], self.rows[-1]
        if level <= lo["level"]:
            row = lo
        elif level >= hi["level"]:
            row = hi
        else:
            a, b = next((a, b) for a, b in zip(self.rows, self.rows[1:]) if a["level"] <= level <= b["level"])
            t = (level - a["level"]) / (b["level"] - a["level"])
            row = {k: a[k] + t * (b[k] - a[k]) for k in a}

        def weapon(prefix: str):
            if row[f"{prefix}_speed"] <= 0:
                return None
            return (round(row[f"{prefix}_min"]), round(row[f"{prefix}_max"]), round(row[f"{prefix}_speed"], 2))

        plain = {f.name: row[f.name] for f in fields(MeleeStats) if f.name not in WEAPON_COLUMNS and f.name != "level"}
        return MeleeStats(level=level, **plain, **{name: weapon(p) for name, p in WEAPON_COLUMNS.items()})


@dataclass(frozen=True)
class Output:
    dps: float
    mana_per_second: float
    fallback_dps: float   # DPS once out of mana (hunters: Auto Shot); equals dps for rogues


def _config() -> dict:
    return tomllib.loads(CONFIG.read_text(encoding="utf-8"))


def _has_pet(cls: ClassData, ranks: Mapping[int, int]) -> bool:
    lone = next((t for t in cls.talents if t.name == "Lone Wolf"), None)
    return lone is None or ranks.get(lone.talent_id, 0) <= 0


@dataclass(frozen=True)
class HybridStats:
    """A caster class with melee builds (#175): its caster row and its melee row at one level.
    Level, health and mana come from the caster row."""

    caster: Any
    melee: MeleeStats

    @property
    def level(self) -> int:
        return self.caster.level

    @property
    def health(self) -> float:
        return self.caster.health

    @property
    def mana(self) -> float:
        return self.caster.mana


class HybridTable:
    def __init__(self, caster, melee: MeleeStatTable):
        self.caster, self.melee = caster, melee

    def at(self, level: int) -> HybridStats:
        return HybridStats(self.caster.at(level), self.melee.at(level))


def stat_table(class_name: str):
    """The class's per-level stats: a caster's (config/stats/<class>.csv, mage format, #163), a
    hybrid's caster and melee rows (#175), or a melee/ranged class's."""
    from wowforever.classes import class_module

    module = class_module(class_name)
    if getattr(module, "ENGINE", None) == "spell":
        from wowforever.stats import StatTable

        caster = StatTable.load(class_name)
        if getattr(module, "MELEE_TREES", ()):
            return HybridTable(caster, MeleeStatTable.load(f"{class_name}_melee"))
        return caster
    return MeleeStatTable.load(class_name)


def build_stats(class_name: str, stats, cls: ClassData, ranks: Mapping[int, int]):
    """The stats row a build fights with: a hybrid's melee row for its melee builds, else `stats`."""
    if isinstance(stats, HybridStats):
        from wowforever.classes import class_module

        return stats.melee if main_tree(cls, ranks) in class_module(class_name).MELEE_TREES else stats.caster
    return stats


def main_tree(cls: ClassData, ranks: Mapping[int, int]) -> str:
    """The tree holding most of the build's points."""
    points = {t.name: sum(ranks.get(i, 0) for i in t.talent_ids) for t in cls.trees}
    return max(points, key=points.get)


def rotation_output(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                    ranks: Mapping[int, int], target: Target, *, drink_mana_per_second: float | None = None) -> Output:
    """The class rotation's DPS, mana use and out-of-mana fallback against `target`."""
    from wowforever.classes import class_module

    module = class_module(class_name)
    if isinstance(stats, HybridStats):
        if main_tree(cls, ranks) in module.MELEE_TREES:
            if class_name == "druid":
                from wowforever.classes.druid_rotation import cat_rotation

                r = cat_rotation(stats.melee, spells, cls, ranks, target)
            else:
                from wowforever.classes.shaman_rotation import enhancement_rotation

                r = enhancement_rotation(stats.melee, spells, cls, ranks, target)
            return Output(r.dps, 0.0, r.dps)
        stats = stats.caster
    if getattr(module, "ENGINE", None) == "spell":
        from wowforever.caster import caster_rotation

        r = caster_rotation(class_name, stats, spells, cls, ranks, target, drink_mana_per_second=drink_mana_per_second)
        gross = r.mana_per_second + r.regen_per_second
        # once dry, a caster keeps casting at the rate its regen pays for
        return Output(r.dps, r.mana_per_second, r.dps * min(1.0, r.regen_per_second / gross) if gross > 0 else r.dps)
    if class_name == "rogue":
        from wowforever.classes.rogue_rotation import rogue_rotation

        r = rogue_rotation(stats, spells, cls, ranks, target)
        return Output(r.dps, 0.0, r.dps)
    if class_name == "hunter":
        from wowforever.classes.hunter_rotation import hunter_rotation

        r = hunter_rotation(stats, spells, cls, ranks, target, pet=_has_pet(cls, ranks))
        return Output(r.dps, r.mana_per_second, r.auto_dps + r.pet_dps)
    if class_name == "paladin":
        from wowforever.classes.paladin_rotation import paladin_rotation

        r = paladin_rotation(stats, spells, cls, ranks, target)
        return Output(r.dps, 0.0, r.dps)
    if class_name == "warrior":
        from wowforever.classes.warrior_rotation import warrior_rotation

        r = warrior_rotation(stats, spells, cls, ranks, target)
        return Output(r.dps, 0.0, r.dps)
    raise ValueError(f"no melee rotation for {class_name!r}")


def questing(class_name: str, stats: MeleeStats, spells, cls, ranks) -> float:
    """Kills per hour against same-level mobs: kill time + recovery downtime + travel."""
    level = stats.level
    q = default_params("questing", level)
    armor, mob_dps, eat = _anchor_at(_config()["questing"]["anchors"], level)
    out = rotation_output(class_name, stats, spells, cls, ranks, Target(0, armor),
                          drink_mana_per_second=q.drink_mana_per_second)
    kill = q.mob_hp / out.dps
    if class_name != "hunter" or not _has_pet(cls, ranks):
        downtime = mob_dps * kill / eat
    else:
        downtime = 0.0
    if out.mana_per_second > 0:
        downtime = max(downtime, out.mana_per_second * kill / q.drink_mana_per_second)
    return 3600 / (kill + downtime + q.travel_seconds)


def dungeon(class_name: str, stats: MeleeStats, spells, cls, ranks) -> float:
    """DPS on a level+2 dungeon pull with tank debuffs (one minute; mana isn't limiting)."""
    d = _config()["dungeon"]
    armor = _anchor_at(_config()["questing"]["anchors"], stats.level)[0] * d["armor_share_of_questing"]
    return rotation_output(class_name, stats, spells, cls, ranks,
                           Target(d["target_level_offset"], armor)).dps


def raid(class_name: str, stats: MeleeStats, spells, cls, ranks) -> float:
    """Sustained DPS against a debuffed boss over the mage's fight-length mix; hunters spend the
    same mana budget (pool, Mana Ruby, potions and runes, Blessing of Wisdom), then Auto Shot."""
    r = _config()["raid"]
    out = rotation_output(class_name, stats, spells, cls, ranks, Target(r["target_level_offset"], r["armor"]))
    p = default_params("raid", stats.level)
    drain = out.mana_per_second - p.mana_per_second
    lengths = p.fight_lengths or ((p.fight_seconds, 1.0),)
    total = weight = 0.0
    for seconds, w in lengths:
        if drain <= 0:
            score = out.dps
        else:
            budget = stats.mana + p.extra_mana + sum(m * math.ceil(seconds / cd) for m, cd in p.consumables)
            full = min(seconds, budget / drain)
            score = (out.dps * full + out.fallback_dps * (seconds - full)) / seconds
        total += score * w
        weight += w
    return total / weight


def pve_score(class_name: str, stats_at_max: MeleeStats, spells, cls, ranks) -> float:
    """Mean of questing, raid and dungeon, each divided by its reference."""
    ref = _config()["references"]
    return (questing(class_name, stats_at_max, spells, cls, ranks) / ref["questing"]
            + raid(class_name, stats_at_max, spells, cls, ranks) / ref["raid"]
            + dungeon(class_name, stats_at_max, spells, cls, ranks) / ref["dungeon"]) / 3
