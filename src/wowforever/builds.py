"""Build definitions from `config/builds/*.toml`, resolved against a class's talents.

A build names talents (names survive patches better than ids) and gives either a final
allocation (`[final]`, talent = rank) or a full point order (`order`, one name per point from
the first talent level); with an order, the final allocation is derived from it.
"""

from __future__ import annotations

import tomllib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from wowforever.schema import ClassData

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "builds"


@dataclass(frozen=True)
class Build:
    id: str
    name: str
    summary: str
    final: dict[str, int]                      # talent name -> rank
    order: tuple[str, ...] | None = None       # talent name per point, or None
    must_have_by: dict[str, int] = field(default_factory=dict)  # talent name -> level
    gives_up: tuple[str, ...] = ()
    primary_spell: str = ""                    # main nuke; leveling orders are optimized around it
    pair: str = ""                             # builds sharing a pair id are PvP/PvE variants (dual spec, #41)
    variant: str = ""                          # "PvP" or "PvE"
    origin: str = "hand"                       # "community" (consensus/popularity data), "hand", or "model"
    sources: tuple[str, ...] = ()              # keys into config/consensus.toml [sources]
    confidence: str = ""                       # low | medium | high, for community builds

    @classmethod
    def load(cls, path: Path) -> Build:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        order = tuple(raw["order"]) if "order" in raw else None
        final = dict(Counter(order)) if order else dict(raw["final"])
        return cls(raw["id"], raw["name"], raw["summary"], final, order,
                   dict(raw.get("must_have_by", {})), tuple(raw.get("gives_up", ())),
                   raw.get("primary_spell", ""), raw.get("pair", raw["id"]), raw.get("variant", ""),
                   raw.get("origin", "hand"), tuple(raw.get("sources", ())), raw.get("confidence", ""))

    def unknown_talents(self, cls: ClassData) -> list[str]:
        """Talent names in this build that the class doesn't have (e.g. renamed by a patch)."""
        known = {t.name.lower() for t in cls.talents}
        names = set(self.final) | set(self.must_have_by) | set(self.order or ())
        return sorted(n for n in names if n.lower() not in known)

    def final_ids(self, cls: ClassData) -> dict[int, int]:
        return {cls.talent_named(n).talent_id: r for n, r in self.final.items()}

    def order_ids(self, cls: ClassData) -> list[int] | None:
        return [cls.talent_named(n).talent_id for n in self.order] if self.order else None


def load_builds(directory: Path = CONFIG_DIR) -> list[Build]:
    return [Build.load(p) for p in sorted(directory.glob("*.toml"))]
