"""Resolve a taken talent list into Modifiers for the EV engine (#51)."""

from __future__ import annotations

from collections.abc import Mapping, Set

from wowforever.calc.ev import Modifiers
from wowforever.schema import ClassData, SpellRank

# Effect kind -> Modifiers field; kinds not listed don't affect Modifiers.
_KIND_TO_FIELD = {
    "damage_pct": "damage_pct",
    "crit_chance": "crit_chance_bonus",
    "crit_damage_pct": "crit_damage_bonus_pct",
    "dot_pct": "ignite_pct",
    "cast_time": "cast_time_delta",
    "mana_cost_pct": "mana_cost_pct",
    "hit_chance": "hit_bonus",
}


def modifiers_for(spell: SpellRank, cls: ClassData, ranks: Mapping[int, int],
                  conditions: Set[str] = frozenset()) -> Modifiers:
    """Sum each taken talent's rank value onto the Modifiers fields its effects drive."""
    totals: dict[str, float] = {}
    for talent_id, rank in ranks.items():
        if rank <= 0:  # values[rank - 1] would wrap around to the max-rank value
            continue
        talent = cls.talent(talent_id)
        for effect in talent.effects:
            field = _KIND_TO_FIELD.get(effect.kind)
            if field is None or not _applies(effect.applies_to, spell, conditions):
                continue
            totals[field] = totals.get(field, 0.0) + effect.values[rank - 1]
    return Modifiers(**totals)


def _applies(applies_to: tuple[str, ...], spell: SpellRank, conditions: Set[str]) -> bool:
    """True when the tokens target the spell's school/name and every @condition holds."""
    if not any(token == "all" or token in spell.schools or token == spell.name
               for token in applies_to if not token.startswith("@")):
        return False
    return all(token[1:] in conditions for token in applies_to if token.startswith("@"))
