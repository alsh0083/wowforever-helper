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


def caster_output(class_name: str, stats: Any, spells: Sequence[SpellRank], cls: ClassData,
                  ranks: Mapping[int, int], target: Target, *, drink_mana_per_second: float | None = None) -> Any:
    """The caster rotation's Output (caster.py, #163); once dry, a caster keeps casting at the rate its
    regen pays for."""
    from wowforever.caster import caster_rotation
    from wowforever.gear import caster_config
    from wowforever.melee_scenarios import Output

    r = caster_rotation(class_name, stats, spells, cls, ranks, target, drink_mana_per_second=drink_mana_per_second)
    gross = r.mana_per_second + r.regen_per_second
    fallback = r.dps * min(1.0, r.regen_per_second / gross) if gross > 0 else r.dps
    cfg = caster_config(class_name)
    if "life_tap" in cfg:
        fallback = life_tap_fallback(r.dps, r.mana_per_second, stats.level, cfg["life_tap"])
    return Output(r.dps, r.mana_per_second, fallback, ranged=True)


def life_tap_fallback(dps: float, drain: float, level: int, tap) -> float:
    """Once dry, the warlock taps instead of waiting on regen (#348): one GCD per tap, the highest rank
    the level can use, and its mana (rank base + 1 per level above the rank)."""
    if drain <= 0:
        return dps
    rank = max((r for r in tap["ranks"] if r[0] <= level), key=lambda r: r[0])
    return dps / (1 + drain * tap["gcd"] / (rank[1] + level - rank[0]))


def caster_aoe(class_name: str, stats: Any, spells: Sequence[SpellRank], cls: ClassData,
               ranks: Mapping[int, int], *, pack: int, mob_hp: float) -> tuple[float, str]:
    """A caster's AoE spells mixed into its rotation (caster.aoe_pull, #260)."""
    from wowforever.caster import aoe_pull

    pull = aoe_pull(class_name, stats, spells, cls, ranks, pack, mob_hp)
    return pull.seconds, pull.spell


def melee_build(melee_trees: Sequence[str], cls: ClassData, ranks: Mapping[int, int]) -> bool:
    """A hybrid's build fights in melee when most of its points sit in a melee tree (#175)."""
    from wowforever.melee_scenarios import main_tree

    return main_tree(cls, ranks) in melee_trees


def hybrid_output(class_name: str, melee_trees: Sequence[str], melee_output: Callable[..., Any], stats: Any,
                  spells: Sequence[SpellRank], cls: ClassData, ranks: Mapping[int, int], target: Target, *,
                  pack: int = 1, drink_mana_per_second: float | None = None, melee: bool | None = None) -> Any:
    """A hybrid's Output: its melee rotation on the melee stat row for a melee build (or `melee=True`, a
    Feral leveling path while its points sit in Balance), else the caster rotation on the caster row."""
    from wowforever.melee_scenarios import HybridStats

    if isinstance(stats, HybridStats):
        if melee if melee is not None else melee_build(melee_trees, cls, ranks):
            return melee_output(stats.melee, spells, cls, ranks, target, pack=pack)
        stats = stats.caster
    return caster_output(class_name, stats, spells, cls, ranks, target, drink_mana_per_second=drink_mana_per_second)


def hybrid_aoe(class_name: str, melee_trees: Sequence[str], output: Callable[..., Any], stats: Any,
               spells: Sequence[SpellRank], cls: ClassData, ranks: Mapping[int, int], *,
               pack: int, mob_hp: float, armor: float) -> tuple[float, str]:
    """A melee build runs its rotation against the pack; a caster build mixes in its AoE spells."""
    from wowforever.melee_scenarios import HybridStats

    if isinstance(stats, HybridStats) and melee_build(melee_trees, cls, ranks):
        return pack_aoe(output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)
    row = stats.caster if isinstance(stats, HybridStats) else stats
    return caster_aoe(class_name, row, spells, cls, ranks, pack=pack, mob_hp=mob_hp)


def caster_facts(class_name: str, plan: Mapping[str, Sequence[str]], stats: Any, cls: ClassData,
                 ranks: Mapping[int, int]) -> dict[str, Any]:
    """The caster rotation's DoTs, cooldowns and filler at level 60 against a level-60 target."""
    from wowforever.caster import caster_rotation

    r = caster_rotation(class_name, stats, cls.spells, cls, ranks, Target(0, 0))
    return {"kind": "caster", "dots": [s for s in r.spells if s in plan.get("dots", ())],
            "cooldowns": [s for s in r.spells if s in plan.get("cooldowns", ())],
            "filler": next((s for s in r.spells if s in plan.get("fillers", ())), None)}


def hybrid_facts(class_name: str, melee_trees: Sequence[str], melee_facts: Callable[..., dict[str, Any]],
                 plan: Mapping[str, Sequence[str]], stats: Any, cls: ClassData,
                 ranks: Mapping[int, int]) -> dict[str, Any]:
    """A melee build's melee facts on its melee row, else the caster facts on the caster row."""
    from wowforever.melee_scenarios import HybridStats

    if isinstance(stats, HybridStats):
        if melee_build(melee_trees, cls, ranks):
            return melee_facts(stats.melee, cls, ranks)
        stats = stats.caster
    return caster_facts(class_name, plan, stats, cls, ranks)


def one_side(class_name: str, stats: Any, spells: Sequence[SpellRank], cls: ClassData,
             ranks: Mapping[int, int]) -> list[tuple[None, Any]]:
    """A class with one way to duel: its class_pvp side, unnamed."""
    from wowforever.pvp.class_pvp import class_side

    return [(None, class_side(class_name, stats, spells, cls, ranks))]
