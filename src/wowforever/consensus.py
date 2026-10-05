"""Consensus-backed scenario weights and talent tiers, read from `config/consensus.toml` (#24).

Confidence rule (owner decision, #23): evidence from Classic/TBC counts at full confidence only
for talents Forever left unchanged; a tier entry backed only by older-era sources whose talent
Forever changed is reported as low confidence.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from wowforever.schema import ClassData

CONFIG = Path(__file__).resolve().parents[2] / "config" / "consensus.toml"
AXES = ("kill", "endurance", "survival", "control")
CONFIDENCE = ("low", "medium", "high")
TIERS = ("core", "strong", "situational")


@dataclass(frozen=True)
class ScenarioWeights:
    name: str
    ranges: dict[str, tuple[float, float, float]]  # axis -> (low, mid, high)
    sources: tuple[str, ...]
    confidence: str
    note: str

    def mid(self) -> dict[str, float]:
        return {axis: r[1] for axis, r in self.ranges.items()}


@dataclass(frozen=True)
class Consensus:
    sources: dict[str, dict]
    scenarios: dict[str, ScenarioWeights]
    tiers: dict[str, dict[str, tuple[str, ...]]]  # scenario -> {"core": (...), "strong": (...), "sources": (...)}

    @classmethod
    def load(cls, path: Path = CONFIG) -> Consensus:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        scenarios = {
            name: ScenarioWeights(name, {a: tuple(s[a]) for a in AXES}, tuple(s["sources"]),
                                  s["confidence"], s.get("note", ""))
            for name, s in raw["scenario"].items()
        }
        tiers = {name: {k: tuple(v) for k, v in t.items()} for name, t in raw.get("tiers", {}).items()}
        return cls(raw["sources"], scenarios, tiers)

    def problems(self, mage: ClassData | None = None) -> list[str]:
        """Structural problems; with class data, also tier names that aren't talents."""
        out = []
        for s in self.scenarios.values():
            total = sum(s.mid().values())
            if abs(total - 1.0) > 1e-6:
                out.append(f"{s.name}: axis mids sum to {total:.3f}, not 1")
            for axis, (lo, mid, hi) in s.ranges.items():
                if not 0 <= lo <= mid <= hi <= 1:
                    out.append(f"{s.name}/{axis}: range {lo}-{mid}-{hi} out of order")
            if s.confidence not in CONFIDENCE:
                out.append(f"{s.name}: bad confidence {s.confidence!r}")
            out += [f"{s.name}: unknown source {src!r}" for src in s.sources if src not in self.sources]
        for name, t in self.tiers.items():
            out += [f"tiers.{name}: unknown source {src!r}" for src in t.get("sources", ())
                    if src not in self.sources]
            if mage is not None:
                known = {x.name for x in mage.talents}
                out += [f"tiers.{name}: {n!r} is not a talent" for tier in TIERS
                        for n in t.get(tier, ()) if n not in known]
        return out

    def tier_confidence(self, scenario: str, talent: str, mage: ClassData) -> str:
        """Confidence of one tier entry: low when all its sources predate Forever and Forever
        changed the talent; otherwise the scenario's confidence."""
        eras = {self.sources[s]["era"] for s in self.tiers[scenario].get("sources", ())}
        status = mage.talent_named(talent).classic_status
        if eras and "forever" not in eras and status not in ("same", None):
            return "low"
        return self.scenarios[scenario].confidence if scenario in self.scenarios else "low"
