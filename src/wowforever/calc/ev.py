"""Expected-value core for spell damage (#17).

Pure functions over `wowforever.schema.SpellRank`; rules are the Classic-era spell rules
worked out in `tests/test_ev_golden.py` (miss by level difference, 150% base crit with a
scalable bonus, fire-school Ignite, periodic damage). Level-based resistance (#409) is an average partial
resist, when the caller asks for it.
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
    direct_damage_pct: float = 0.0   # the initial hit only (Aftermath, #384)
    resistance_reduction: float = 0.0   # resistance taken off the target (Arcane Subtlety, #409)


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


def level_resist_pct(caster_level: int, target_level: int, reduction: float = 0.0) -> float:
    """Average % of spell damage a higher-level target resists (#409, Classic): 8 resistance per level above the
    caster, less `reduction`, resisted on average resistance / (caster level x 5) x 0.75."""
    resistance = max(0.0, 8.0 * (target_level - caster_level) - reduction)
    return resistance / (caster_level * 5.0) * 0.75 * 100.0


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
    level_resistance: bool = False,
) -> float:
    """Expected damage per cast: direct + periodic + Ignite (fire-school spells only)."""
    damage_factor = 1.0 + mods.damage_pct / 100.0
    avg = (((spell.min_damage + spell.max_damage) / 2.0 + spell.coefficient * spell_power) * damage_factor
           * (1.0 + mods.direct_damage_pct / 100.0))
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

    total = direct + periodic + ignite
    if level_resistance and "holy" not in spell.schools:
        total *= 1.0 - level_resist_pct(caster_level, target_level, mods.resistance_reduction) / 100.0
    return total
