"""Switchable assumptions for unknown mechanics, read from `config/assumptions.toml`.

Each assumption has a default `value` and its allowed `options`. Scenario code reads values
through `Assumptions`; `variants()` yields every combination of the named switches so a
report can show which unknowns change a ranking.
"""

from __future__ import annotations

import itertools
import tomllib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG = Path(__file__).resolve().parents[2] / "config" / "assumptions.toml"


@dataclass(frozen=True)
class Assumption:
    name: str
    value: Any
    options: tuple[Any, ...]
    why: str
    source: str
    tested: str = ""
    talents: tuple[str, ...] = ()


@dataclass(frozen=True)
class Assumptions:
    entries: Mapping[str, Assumption]
    overrides: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = CONFIG) -> Assumptions:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        entries = {
            name: Assumption(name, e["value"], tuple(e["options"]), e["why"], e["source"],
                             e.get("tested", ""), tuple(e.get("talents", ())))
            for name, e in raw.items()
        }
        for a in entries.values():
            if a.value not in a.options:
                raise ValueError(f"{a.name}: default {a.value!r} not in options {a.options}")
        return cls(entries)

    def __getitem__(self, name: str) -> Any:
        if name in self.overrides:
            return self.overrides[name]
        return self.entries[name].value

    def with_values(self, **values: Any) -> Assumptions:
        for name, value in values.items():
            if value not in self.entries[name].options:
                raise ValueError(f"{name}: {value!r} not in options {self.entries[name].options}")
        return Assumptions(self.entries, {**self.overrides, **values})

    def variants(self, *names: str) -> Iterator[Assumptions]:
        """Every combination of the options of `names` (all switches when none are named)."""
        names = names or tuple(self.entries)
        for combo in itertools.product(*(self.entries[n].options for n in names)):
            yield self.with_values(**dict(zip(names, combo)))

    def describe(self) -> dict[str, Any]:
        """Current value of every switch, for recording next to a result."""
        return {name: self[name] for name in self.entries}


def impact_rolls_per_cast(spell_name: str, ticks: int, assumptions: Assumptions) -> int:
    """How many times one cast can roll Impact: the direct hit, plus ticks for Frostfire Bolt
    when `frostfire_ticks_trigger_impact` is on."""
    if spell_name == "Frostfire Bolt" and assumptions["frostfire_ticks_trigger_impact"]:
        return 1 + ticks
    return 1


SUB20_PENALTY_PER_LEVEL = 0.0375


def sub20_penalized(spell, assumptions: Assumptions):
    """`spell` with its spell power coefficients cut for being learned below level 20, when
    `sub20_spell_penalty` is on: x (1 - 0.0375 per level under 20), so a level-4 rank keeps 40%."""
    from dataclasses import replace

    if not assumptions["sub20_spell_penalty"] or spell.level >= 20:
        return spell
    factor = 1.0 - SUB20_PENALTY_PER_LEVEL * (20 - spell.level)
    return replace(spell, coefficient=spell.coefficient * factor,
                   periodic_coefficient=spell.periodic_coefficient * factor)


def periodic_can_crit(spell_name: str, assumptions: Assumptions) -> bool:
    """Whether a spell's periodic part can crit under the current assumptions."""
    return spell_name == "Frostfire Bolt" and bool(assumptions["frostfire_periodic_can_crit"])
