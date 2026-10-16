"""PvE scenarios for rogue and hunter (#133): questing kills/hour, dungeon-pull DPS and sustained raid
DPS, built on their rotations (#131, #132). Constants: config/melee_scenarios.toml, plus the mage's
questing anchors (mob HP, drink rates, travel) and raid mana budget from config/scenarios.toml.

Downtime: rogues and warriors eat back the health a fight costs them; hunters drink back the mana. Hunters
with a pet let it tank; a Lone Wolf hunter's health isn't modeled yet.
"""

from __future__ import annotations

import csv
import dataclasses
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from wowforever.classes import engine
from wowforever.melee_stats import MeleeStats
from wowforever.physical import Target
from wowforever.scenarios import _anchor_at, default_params
from wowforever.schema import ClassData, SpellRank
from wowforever.toml_cache import load_toml

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
    aoe: tuple[str, ...] = ()   # abilities that hit several mobs of a pack (#262)
    pet: bool = False           # a pet fights alongside (and tanks while questing)
    ranged: bool = False        # the rotation fights from range
    spell: str | None = None    # the filler the rotation chose, where it chooses one (mage, #316)
    mana_cooldown: tuple[float, float] | None = None   # (channel seconds, mana) a class spends to
                                                       # refill when a raid fight would run it dry (Evocation, #317)


def _config() -> dict:
    return load_toml(CONFIG)


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
    if getattr(module, "ENGINE", None) in ("spell", True):   # True is the mage's own engine
        from wowforever.stats import StatTable

        caster = StatTable.load(class_name)
        if getattr(module, "MELEE_TREES", ()):
            return HybridTable(caster, MeleeStatTable.load(f"{class_name}_melee"))
        return caster
    return MeleeStatTable.load(class_name)


def build_stats(class_name: str, stats, cls: ClassData, ranks: Mapping[int, int]):
    """The stats row a build fights with: a hybrid's melee row for its melee builds, else `stats`."""
    if isinstance(stats, HybridStats):
        from wowforever.classes import engine

        return stats.melee if engine(class_name).playstyle(cls, ranks) == "melee" else stats.caster
    return stats


def main_tree(cls: ClassData, ranks: Mapping[int, int]) -> str:
    """The tree holding most of the build's points."""
    points = {t.name: sum(ranks.get(i, 0) for i in t.talent_ids) for t in cls.trees}
    return max(points, key=points.get)


def questing(class_name: str, stats: MeleeStats, spells, cls, ranks, *, melee: bool | None = None) -> float:
    """Kills per hour against same-level mobs: kill time + recovery downtime + travel."""
    level = stats.level
    q = default_params("questing", level)
    armor, mob_dps, eat = _anchor_at(_config()["questing"]["anchors"], level)
    out = engine(class_name).output(stats, spells, cls, ranks, Target(0, armor),
                                    drink_mana_per_second=q.drink_mana_per_second, melee=melee)
    kill = q.mob_hp / out.dps
    downtime = 0.0 if out.pet else mob_dps * kill / eat     # a pet tanks while the hunter shoots
    if out.mana_per_second > 0:
        downtime = max(downtime, out.mana_per_second * kill / q.drink_mana_per_second)
    return 3600 / (kill + downtime + q.travel_seconds)


def dungeon(class_name: str, stats: MeleeStats, spells, cls, ranks) -> float:
    """DPS on a level+2 dungeon pull with tank debuffs (one minute, run on the build's mana pool, #348)."""
    d = _config()["dungeon"]
    armor = _anchor_at(_config()["questing"]["anchors"], stats.level)[0] * d["armor_share_of_questing"]
    output = engine(class_name).output(stats, spells, cls, ranks, Target(d["target_level_offset"], armor))
    return dungeon_pull(output, stats.mana, stats.level)


def dungeon_pull(out: Output, mana: float, level: int) -> float:
    """DPS over one dungeon pull (#348): a 60 s pull on the mana pool with no potions and no Evocation."""
    return raid_dps(dataclasses.replace(out, mana_cooldown=None), mana, default_params("dungeon", level))


def raid_dps(out: Output, mana: float, p) -> float:
    """Sustained DPS over a fight-length mix for one Output (#317): full DPS while the mana budget
    (pool + one-off mana + each consumable once per started cooldown) lasts, then fallback DPS;
    when the budget would run dry, `out.mana_cooldown` (channel seconds, mana) refills it and
    costs its channel time (the mage's Evocation)."""
    drain = out.mana_per_second - p.mana_per_second
    lengths = p.fight_lengths or ((p.fight_seconds, 1.0),)
    total = weight = 0.0
    for seconds, w in lengths:
        if drain <= 0:
            score = out.dps
        else:
            budget = mana + p.extra_mana + sum(m * math.ceil(seconds / cd) for m, cd in p.consumables)
            active = seconds
            if out.mana_cooldown is not None and budget / drain < seconds:
                active -= out.mana_cooldown[0]
                budget += out.mana_cooldown[1]
            full = min(active, budget / drain)
            score = (out.dps * full + out.fallback_dps * (active - full)) / seconds
        total += score * w
        weight += w
    return total / weight


def raid(class_name: str, stats: MeleeStats, spells, cls, ranks) -> float:
    """Sustained DPS against a debuffed boss over the mage's fight-length mix; hunters spend the
    same mana budget (pool, Mana Ruby, potions and runes, Blessing of Wisdom), then Auto Shot."""
    r = _config()["raid"]
    out = engine(class_name).output(stats, spells, cls, ranks, Target(r["target_level_offset"], r["armor"]),
                                    sustained=True)
    return raid_dps(out, stats.mana, default_params("raid", stats.level))


def aoe(class_name: str, stats: MeleeStats, spells, cls, ranks) -> tuple[float, str]:
    """Seconds to clear a pack of same-level questing mobs (#263) and the AoE spell used, or "single
    target". Spell-engine classes (and a hybrid's caster builds) mix their AoE spells into the rotation
    (caster.aoe_pull, #260); the others run their rotation against the pack (the engine's `pack`,
    #262), single target where their AoE abilities aren't modeled yet."""
    pack = _config()["aoe"]["pack"]
    mob_hp = default_params("aoe", stats.level).mob_hp
    armor = _anchor_at(_config()["questing"]["anchors"], stats.level)[0]
    return engine(class_name).aoe(stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)


def pve_score(class_name: str, stats_at_max: MeleeStats, spells, cls, ranks) -> float:
    """Mean of questing, raid, dungeon (with a weighted 5-player group, #220) and AoE pulls (#263), each
    divided by its reference (AoE: reference seconds / seconds to clear the pack)."""
    from wowforever import group

    ref = _config()["references"]
    return (questing(class_name, stats_at_max, spells, cls, ranks) / ref["questing"]
            + raid(class_name, stats_at_max, spells, cls, ranks) / ref["raid"]
            + group.typical_dungeon_dps(class_name, stats_at_max, cls, ranks) / ref["dungeon"]
            + ref["aoe_seconds"] / aoe(class_name, stats_at_max, spells, cls, ranks)[0]) / 4
