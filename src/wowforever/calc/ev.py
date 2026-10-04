"""Expected-value core for spell damage (#17).

Pure functions over `wowforever.schema.SpellRank`; rules are the Classic-era spell rules
worked out in `tests/test_ev_golden.py` (miss by level difference, 150% base crit with a
scalable bonus, fire-school Ignite, periodic damage). Resistances are ignored in v0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from wowforever.schema import SpellRank

GCD_SECONDS = 1.5
BASE_CRIT_BONUS_PCT = 50.0
MIN_MISS_PCT = 1.0


@dataclass(frozen=True)
class Modifiers:
    """Gear/talent modifiers layered on a base spell, all percentages unless noted."""

    damage_pct: float = 0.0
    crit_chance_bonus: float = 0.0
    crit_damage_bonus_pct: float = 0.0
    ignite_pct: float = 0.0
    cast_time_delta: float = 0.0
    mana_cost_pct: float = 0.0
    hit_bonus: float = 0.0


def _base_miss_pct(level_diff: int) -> float:
    """Base spell miss percent for target level minus caster level."""
    if level_diff <= 2:
        return 4.0 + level_diff
    return 17.0 + 11.0 * (level_diff - 3)


def miss_chance(caster_level: int, target_level: int, hit_pct: float) -> float:
    """Spell miss chance in percent, lowered by hit and floored at 1%."""
    return max(MIN_MISS_PCT, _base_miss_pct(target_level - caster_level) - hit_pct)


def effective_cast_time(spell: SpellRank, mods: Modifiers) -> float:
    """Cast time in seconds after modifiers, floored at the global cooldown."""
    return max(GCD_SECONDS, spell.cast_time + mods.cast_time_delta)


def casts_to_oom(spell: SpellRank, mana: float, mods: Modifiers) -> int:
    """Full casts affordable before running out of mana."""
    cost = spell.mana_cost * (1.0 + mods.mana_cost_pct / 100.0)
    if cost <= 0:
        raise ValueError(f"{spell.name}: spell has no mana cost")
    return math.floor(mana / cost)


def expected_damage(
    spell: SpellRank,
    *,
    spell_power: float,
    crit_pct: float,
    hit_pct: float,
    caster_level: int,
    target_level: int,
    mods: Modifiers,
    periodic_can_crit: bool = False,
) -> float:
    """Expected damage per cast: direct + periodic + Ignite (fire-school spells only)."""
    damage_factor = 1.0 + mods.damage_pct / 100.0
    avg = ((spell.min_damage + spell.max_damage) / 2.0 + spell.coefficient * spell_power) * damage_factor
    crit = min(100.0, crit_pct + mods.crit_chance_bonus) / 100.0
    hit = 1.0 - miss_chance(caster_level, target_level, hit_pct + mods.hit_bonus) / 100.0
    crit_bonus = (BASE_CRIT_BONUS_PCT / 100.0) * (1.0 + mods.crit_damage_bonus_pct / 100.0)
    crit_factor = 1.0 + crit * crit_bonus

    direct = hit * avg * crit_factor
    periodic_avg = (spell.periodic_damage + spell.periodic_coefficient * spell_power) * damage_factor
    periodic = hit * periodic_avg * (crit_factor if periodic_can_crit else 1.0)
    ignite = 0.0
    if "fire" in spell.schools:
        ignite = hit * crit * (avg * (1.0 + crit_bonus)) * (mods.ignite_pct / 100.0)

    return direct + periodic + ignite
