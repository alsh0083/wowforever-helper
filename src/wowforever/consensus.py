"""Consensus-backed scenario weights and talent tiers, read from `config/consensus.toml` (#24).

Confidence rule (owner decision, #23): evidence from Classic/TBC counts at full confidence only
for talents Forever left unchanged; a tier entry backed only by older-era sources whose talent
Forever changed is reported as low confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wowforever.schema import ClassData
from wowforever.toml_cache import load_toml

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
    tiers: dict[str, dict[str, dict[str, tuple[str, ...]]]]  # class -> scenario -> {"core": (...), "sources": (...)}
    archetypes: dict = None  # shortlist thresholds and recognized hybrids (#28)

    @classmethod
    def load(cls, path: Path = CONFIG) -> Consensus:
        raw = load_toml(path)
        scenarios = {
            name: ScenarioWeights(name, {a: tuple(s[a]) for a in AXES}, tuple(s["sources"]),
                                  s["confidence"], s.get("note", ""))
            for name, s in raw["scenario"].items()
        }
        tiers = {class_name: {name: {k: tuple(v) for k, v in t.items()} for name, t in by_scenario.items()}
                 for class_name, by_scenario in raw.get("tiers", {}).items()}
        return cls(raw["sources"], scenarios, tiers, raw.get("archetypes", {}))

    def tiers_for(self, class_name: str) -> dict[str, dict[str, tuple[str, ...]]]:
        """The class's talent tiers by scenario (#321); empty for a class without any."""
        return self.tiers.get(class_name, {})

    def problems(self, cls: ClassData | None = None) -> list[str]:
        """Structural problems; with a class's data, also its tier names that aren't its talents."""
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
        for class_name, by_scenario in self.tiers.items():
            for name, t in by_scenario.items():
                out += [f"tiers.{class_name}.{name}: unknown source {src!r}" for src in t.get("sources", ())
                        if src not in self.sources]
                if cls is not None and cls.class_name == class_name:
                    known = {x.name for x in cls.talents}
                    out += [f"tiers.{class_name}.{name}: {n!r} is not a talent" for tier in TIERS
                            for n in t.get(tier, ()) if n not in known]
        return out

    def tier_confidence(self, scenario: str, talent: str, cls: ClassData) -> str:
        """Confidence of one tier entry: low when all its sources predate Forever and Forever
        changed the talent; otherwise the scenario's confidence."""
        eras = {self.sources[s]["era"] for s in self.tiers_for(cls.class_name)[scenario].get("sources", ())}
        status = cls.talent_named(talent).classic_status
        if eras and "forever" not in eras and status not in ("same", None):
            return "low"
        return self.scenarios[scenario].confidence if scenario in self.scenarios else "low"
