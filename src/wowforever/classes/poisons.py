"""Rogue poisons (#387): damage per landed weapon hit, and the best poison on each weapon.

Each landed hit of a poisoned weapon applies its poison with the poison's chance (config/rogue.toml; Improved
Poisons adds to it). A poison is a Nature spell, so it lands on the spell hit table. Instant Poison deals its
damage at once and can crit (x1.5 at the rogue's crit, Malice included); Deadly Poison stacks up to
`max_stacks`, each stack dealing its periodic damage over its duration, and both weapons' applications feed
one stack. Vile Poisons raises both.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence

from wowforever.schema import SpellRank

SPELL_CRIT_MULTIPLIER = 1.5


def poison_dps(poison: SpellRank, hits_per_second: float, *, chance_pct: float, land: float, crit: float,
               damage_pct: float, max_stacks: int) -> float:
    """Damage per second of `poison` on a weapon landing `hits_per_second`."""
    applied = hits_per_second * chance_pct / 100 * land
    if poison.periodic_damage > 0 and poison.duration > 0:
        stacks = min(max_stacks, applied * poison.duration)
        return stacks * poison.periodic_damage / poison.duration * (1 + damage_pct / 100)
    average = (poison.min_damage + poison.max_damage) / 2
    return applied * average * (1 + crit * (SPELL_CRIT_MULTIPLIER - 1)) * (1 + damage_pct / 100)


def best_poisons(poisons: Sequence[SpellRank], hits: Sequence[float], *, chance_pct: Mapping[str, float],
                 land: float, crit: float, damage_pct: float, max_stacks: int) -> tuple[float, tuple[str, ...]]:
    """(damage per second, poison name per weapon) of the best poison on each weapon, where `hits` holds each
    weapon's landed hits per second (main hand, then off hand); (0.0, ()) with no poison learned."""
    best: tuple[float, tuple[str, ...]] = (0.0, ())
    for combo in itertools.product(poisons, repeat=len(hits)):
        dps = 0.0
        for poison in {p.name: p for p in combo}.values():
            on = sum(h for h, p in zip(hits, combo) if p.name == poison.name)
            dps += poison_dps(poison, on, chance_pct=chance_pct[poison.name], land=land, crit=crit,
                              damage_pct=damage_pct, max_stacks=max_stacks)
        if dps > best[0]:
            best = (dps, tuple(p.name for p in combo))
    return best
