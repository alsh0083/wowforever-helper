"""Per-level character stat assumptions, read from `config/stats/<class>.csv`."""

from __future__ import annotations

import csv
from dataclasses import dataclass, fields
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "stats"


@dataclass(frozen=True)
class Stats:
    level: int
    intellect: float
    spirit: float
    stamina: float
    spell_power: float
    crit_pct: float
    hit_pct: float
    mana: float
    health: float


class StatTable:
    def __init__(self, anchors: list[Stats]):
        if not anchors:
            raise ValueError("stat table is empty")
        self.anchors = sorted(anchors, key=lambda s: s.level)
        levels = [a.level for a in self.anchors]
        if len(set(levels)) != len(levels):
            raise ValueError("duplicate level in stat table")

    @classmethod
    def load(cls, class_name: str, config_dir: Path = CONFIG_DIR) -> StatTable:
        with open(config_dir / f"{class_name}.csv", newline="", encoding="utf-8") as f:
            return cls([
                Stats(**{k: (int(v) if k == "level" else float(v)) for k, v in row.items()})
                for row in csv.DictReader(f)
            ])

    def at(self, level: int) -> Stats:
        """Stats at `level`, linearly interpolated between anchors; clamped outside the range."""
        lo, hi = self.anchors[0], self.anchors[-1]
        if level <= lo.level:
            return _with_level(lo, level)
        if level >= hi.level:
            return _with_level(hi, level)
        for a, b in zip(self.anchors, self.anchors[1:]):
            if a.level <= level <= b.level:
                t = (level - a.level) / (b.level - a.level)
                values = {
                    f.name: getattr(a, f.name) + t * (getattr(b, f.name) - getattr(a, f.name))
                    for f in fields(Stats) if f.name != "level"
                }
                return Stats(level=level, **values)
        raise AssertionError("unreachable")


def _with_level(s: Stats, level: int) -> Stats:
    return Stats(level=level, **{f.name: getattr(s, f.name) for f in fields(Stats) if f.name != "level"})
