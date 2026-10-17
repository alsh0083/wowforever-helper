"""Weapon-type talents (#386): Weaponmaster (warrior) and Hack and Slash (rogue) give a bonus that
depends on the weapon. The stat tables carry no weapon type, so each scenario takes the branch with the
most DPS (owner decision 2026-10-17): the best weapon for that fight.

Per rank: +1% crit, ignore 3% of the target's armor, or a 1% chance on a landed attack of an extra
attack. Best effort: an extra attack counts as an average attack, so it adds its chance times the
rotation's DPS, all of it white damage.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any

from wowforever.physical import Target
from wowforever.schema import ClassData

BRANCHES = {
    "Weaponmaster": {"axe": "crit", "mace": "armor", "sword": "extra"},
    "Hack and Slash": {"dagger": "crit", "mace": "armor", "sword": "extra"},
}
PER_RANK = {"crit": 1.0, "armor": 3.0, "extra": 1.0}


def best_weapon(run: Callable[[Any, Target], Any], stats: Any, target: Target, cls: ClassData,
                ranks: Mapping[int, int]) -> tuple[Any, str | None]:
    """(result, weapon) with the most DPS, where `run(stats, target)` returns a rotation result with
    `dps` and `white_dps`; weapon is None when the build takes no weapon-type talent."""
    taken = [(t.name, ranks[t.talent_id]) for t in cls.talents
             if t.name in BRANCHES and ranks.get(t.talent_id, 0) > 0]
    if not taken:
        return run(stats, target), None
    name, rank = taken[0]
    best = None
    for weapon, kind in BRANCHES[name].items():
        value = PER_RANK[kind] * rank
        if kind == "crit":
            r = run(replace(stats, crit_pct=stats.crit_pct + value), target)
        elif kind == "armor":
            r = run(stats, replace(target, armor=target.armor * (1 - value / 100)))
        else:
            r = run(stats, target)
            extra = r.dps * value / 100
            r = replace(r, dps=r.dps + extra, white_dps=r.white_dps + extra)
        if best is None or r.dps > best[0].dps:
            best = (r, weapon)
    return best
