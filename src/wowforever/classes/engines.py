"""Shared ClassEngine pieces (docs/planning/2026-10-14-class-engine.md): class modules bind these
instead of each writing its own."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from wowforever.physical import Target
from wowforever.schema import ClassData, SpellRank


def pack_aoe(output: Callable[..., Any], stats: Any, spells: Sequence[SpellRank], cls: ClassData,
             ranks: Mapping[int, int], *, pack: int, mob_hp: float, armor: float) -> tuple[float, str]:
    """Seconds to clear the pack with the rotation run against it (`output(pack=...)`, #262), and its
    AoE abilities, or "single target" where none hit several mobs."""
    out = output(stats, spells, cls, ranks, Target(0, armor), pack=pack)
    return pack * mob_hp / out.dps, ", ".join(out.aoe) or "single target"


def facts_later(stats: Any, cls: ClassData, ranks: Mapping[int, int]) -> dict[str, Any]:
    """Placeholder until the adapters gain their facts (#312)."""
    raise NotImplementedError("rotation facts move behind the class engine in #312")
