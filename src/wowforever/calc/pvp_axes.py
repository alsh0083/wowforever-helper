"""Survival and control axes for PvP builds (#25).

Each axis is a weighted sum of min(1, component / reference) over its components; weights and
references come from `config/pvp_axes.toml` and the component formulas are fixed by the
hand-worked golden values in `tests/test_pvp_axes.py`.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wowforever.calc.ev import effective_cast_time
from wowforever.calc.talents import modifiers_for
from wowforever.scenarios import Character, best_rank
from wowforever.schema import SpellRank

CONFIG = Path(__file__).resolve().parents[3] / "config" / "pvp_axes.toml"

# Freeze and stun durations are fixed in the talent text (Frostbite: "Freeze the target for
# 5 sec", Impact: "stun the target for 2 sec"); the rules above only parse the chances.
FROSTBITE_FREEZE_SECONDS = 5.0
IMPACT_STUN_SECONDS = 2.0

_CONFIG: dict[str, Any] | None = None


def _config() -> dict[str, Any]:
    """The pvp_axes config, read once per process."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    return _CONFIG


@dataclass(frozen=True)
class AxisScore:
    """A 0-1 axis score plus the raw component values behind it (before shares)."""

    score: float
    components: dict[str, float]


def talent_rank(char: Character, name: str) -> int:
    """Rank of talent `name` taken on `char`, 0 when absent."""
    return char.ranks.get(char.cls.talent_named(name).talent_id, 0)


def effect_value(char: Character, talent: str, kind: str) -> float:
    """Value of `kind` at the taken rank of `talent`, 0 when not taken or not modeled."""
    rank = talent_rank(char, talent)
    if rank <= 0:
        return 0.0
    for effect in char.cls.talent_named(talent).effects:
        if effect.kind == kind:
            return effect.values[rank - 1]
    return 0.0


def _talent_spell(char: Character, talent: str, spell: str) -> SpellRank | None:
    """Highest-rank `spell` learned by `char.level`, counted only when `talent` is taken.

    Ice Barrier, Ice Block and Cold Snap are taught by talents: the value comes from the
    learned spell rank, but a character without the talent gets none of it."""
    if talent_rank(char, talent) <= 0:
        return None
    return best_rank(char.spells, spell, char.level)


def _filler_cast(char: Character, filler: SpellRank) -> float:
    """Seconds per filler cast after talent cast-time reductions."""
    return effective_cast_time(filler, modifiers_for(filler, char.cls, char.ranks))


def survival(char: Character, filler: SpellRank) -> AxisScore:
    """Survival axis: damage shielding, immunity, pushback protection and escapes."""
    barrier = _talent_spell(char, "Ice Barrier", "Ice Barrier")
    ice_block = _talent_spell(char, "Ice Block", "Ice Block")
    cold_snap = _talent_spell(char, "Cold Snap", "Cold Snap")

    components: dict[str, float] = {}
    components["barrier"] = (barrier.absorb * 60 / barrier.cooldown / char.stats.health
                             if barrier else 0.0)
    if ice_block:
        uses = 600 / ice_block.cooldown + (1 if cold_snap else 0)
        components["immunity"] = ice_block.immunity * uses / 600
    else:
        components["immunity"] = 0.0
    pushback = (effect_value(char, "Burning Soul", "pushback_pct") / 100
                if "fire" in filler.schools else 0.0)
    if barrier:
        pushback += _config()["barrier_pushback_share"]
    components["pushback"] = min(1.0, pushback)

    escapes = 0.0
    blink = best_rank(char.spells, "Blink", char.level)
    if blink:
        escapes += 60 / blink.cooldown
    frost_nova = best_rank(char.spells, "Frost Nova", char.level)
    if frost_nova:
        escapes += 60 / (frost_nova.cooldown + effect_value(char, "Improved Frost Nova", "cooldown"))
    components["escapes"] = escapes
    return _score("survival", components)


def control(char: Character, filler: SpellRank) -> AxisScore:
    """Control axis: slow uptime, roots, stuns and interrupts."""
    cast = _filler_cast(char, filler)
    per_min = 60 / cast
    chills = filler.slow_pct > 0
    fire_hit = "fire" in filler.schools

    components: dict[str, float] = {}
    if chills:
        duration = filler.duration * (1 + effect_value(char, "Permafrost", "duration") / 100)
        strength = (filler.slow_pct + effect_value(char, "Permafrost", "slow_pct")) / 100
        components["slow"] = min(1.0, duration / cast) * strength
    else:
        components["slow"] = 0.0

    root = 0.0
    frost_nova = best_rank(char.spells, "Frost Nova", char.level)
    if frost_nova:
        root += frost_nova.root * 60 / (frost_nova.cooldown
                                        + effect_value(char, "Improved Frost Nova", "cooldown"))
    if chills:
        root += effect_value(char, "Frostbite", "proc_chance") / 100 * per_min * FROSTBITE_FREEZE_SECONDS
    components["root"] = root

    components["stun"] = (effect_value(char, "Impact", "proc_chance") / 100 * per_min
                          * IMPACT_STUN_SECONDS if fire_hit else 0.0)

    counterspell = best_rank(char.spells, "Counterspell", char.level)
    components["interrupt"] = ((counterspell.interrupt_lockout
                                + effect_value(char, "Improved Counterspell", "control"))
                               * 60 / counterspell.cooldown if counterspell else 0.0)
    return _score("control", components)


def _score(axis: str, components: dict[str, float]) -> AxisScore:
    """Weighted sum of min(1, component / reference) over the axis' components in the config."""
    spec = _config()[axis]
    score = sum(s["weight"] * min(1.0, components[name] / s["reference"])
                for name, s in spec.items())
    return AxisScore(score, components)
