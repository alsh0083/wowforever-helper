"""PvE scenarios for rogue and hunter (#133): questing kills/hour, dungeon-pull DPS and sustained raid
DPS, built on their rotations (#131, #132). Constants: config/melee_scenarios.toml, plus the mage's
questing anchors (mob HP, drink rates, travel) and raid mana budget from config/scenarios.toml.

Downtime: rogues eat back the health a fight costs them; hunters drink back the mana. Hunters
with a pet let it tank; a Lone Wolf hunter's health isn't modeled yet.
"""

from __future__ import annotations

import csv
import math
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from pathlib import Path

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


def rotation_output(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                    ranks: Mapping[int, int], target: Target) -> Output:
    """The class rotation's DPS, mana use and out-of-mana fallback against `target`."""
    if class_name == "rogue":
        from wowforever.classes.rogue_rotation import rogue_rotation

        r = rogue_rotation(stats, spells, cls, ranks, target)
        return Output(r.dps, 0.0, r.dps)
    if class_name == "hunter":
        from wowforever.classes.hunter_rotation import hunter_rotation

        r = hunter_rotation(stats, spells, cls, ranks, target, pet=_has_pet(cls, ranks))
        return Output(r.dps, r.mana_per_second, r.auto_dps + r.pet_dps)
    raise ValueError(f"no melee rotation for {class_name!r}")


def questing(class_name: str, stats: MeleeStats, spells, cls, ranks) -> float:
    """Kills per hour against same-level mobs: kill time + recovery downtime + travel."""
    level = stats.level
    q = default_params("questing", level)
    armor, mob_dps, eat = _anchor_at(_config()["questing"]["anchors"], level)
    out = rotation_output(class_name, stats, spells, cls, ranks, Target(0, armor))
    kill = q.mob_hp / out.dps
    if class_name == "rogue" or not _has_pet(cls, ranks):
        downtime = mob_dps * kill / eat
    else:
        downtime = 0.0
    if out.mana_per_second > 0:
        downtime = max(downtime, out.mana_per_second * kill / q.drink_mana_per_second)
    return 3600 / (kill + downtime + q.travel_seconds)


def dungeon(class_name: str, stats: MeleeStats, spells, cls, ranks) -> float:
    """DPS on a level+2 dungeon pull with tank debuffs (one minute; mana isn't limiting)."""
    d = _config()["dungeon"]
    return rotation_output(class_name, stats, spells, cls, ranks,
                           Target(d["target_level_offset"], d["armor"])).dps


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
