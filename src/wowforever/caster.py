"""Caster spell engine (#163): one sustained single-target rotation for any caster class.

A class declares `ROTATION = {"dots": [...], "cooldowns": [...], "fillers": [...]}` in its module:
DoTs are kept up (recast once per duration), cooldown nukes go out on cooldown, and the remaining
time goes to the filler with the best damage per second. Each cast's expected damage comes from the
mage's EV engine (`calc.ev.expected_damage`) with the class's talent modifiers, so effect rules by
school or spell name work as they do for the mage. Mana: the rotation's cost per second minus the
talented share of spirit regen while casting (config/casters.toml).

Not modeled here: procs, cleave or AoE, pets (warlock, #165) and Life Tap; classes add those.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from wowforever.assumptions import Assumptions, periodic_can_crit, sub20_penalized
from wowforever.calc.ev import GCD_SECONDS, effective_cast_time, expected_damage
from wowforever.calc.talents import modifiers_for
from wowforever.classes import class_module
from wowforever.gear import caster_config
from wowforever.physical import Target
from wowforever.scenarios import best_rank, scaled
from wowforever.schema import ClassData, SpellRank
from wowforever.stats import Stats


@dataclass(frozen=True)
class CasterRotation:
    dps: float
    mana_per_second: float      # rotation cost minus regen while casting
    regen_per_second: float     # spirit regen while casting (talents)
    spells: tuple[str, ...]     # spells the rotation casts: DoTs, cooldowns, then the filler


def spirit_regen(class_name: str, stats: Stats) -> float:
    """Mana per second outside the five-second rule (Classic per-class formula, per 2 s tick)."""
    cfg = caster_config(class_name)
    return (cfg["regen_base"] + stats.spirit / cfg["regen_spirit_div"]) / 2


def regen_while_casting(class_name: str, stats: Stats, cls: ClassData, ranks: Mapping[int, int]) -> float:
    """The talented share of spirit regen that continues while casting (Meditation, Reflection)."""
    share = sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                for e in t.effects if e.kind == "regen_while_casting")
    return spirit_regen(class_name, stats) * share / 100


def cast(spell: SpellRank, stats: Stats, cls: ClassData, ranks: Mapping[int, int], target_level: int,
         assumptions: Assumptions) -> tuple[float, float, float]:
    """(expected damage, seconds of casting, mana) for one cast; instants take a global cooldown and
    channels their full duration."""
    mods = modifiers_for(spell, cls, ranks)
    ev = expected_damage(sub20_penalized(scaled(spell, stats.level), assumptions),
                         spell_power=stats.spell_power, crit_pct=stats.crit_pct, hit_pct=stats.hit_pct,
                         caster_level=stats.level, target_level=target_level, mods=mods,
                         periodic_can_crit=periodic_can_crit(spell.name, assumptions))
    seconds = max(GCD_SECONDS, effective_cast_time(spell, mods))
    if spell.channeled:
        seconds = max(seconds, spell.duration)
    return ev, seconds, spell.mana_cost * (1 + mods.mana_cost_pct / 100)


def caster_rotation(class_name: str, stats: Stats, spells: Sequence[SpellRank], cls: ClassData,
                    ranks: Mapping[int, int], target: Target) -> CasterRotation:
    """Sustained DPS and mana use against `target` with the class's ROTATION and talents `ranks`."""
    plan = class_module(class_name).ROTATION
    assumptions = Assumptions.load()
    target_level = stats.level + target.level_diff
    time_left, dps, mana, used = 1.0, 0.0, 0.0, []

    def learned(name: str) -> SpellRank | None:
        return best_rank(spells, name, stats.level)

    for kind in ("dots", "cooldowns"):
        for name in plan.get(kind, ()):
            spell = learned(name)
            if spell is None:
                continue
            ev, seconds, cost = cast(spell, stats, cls, ranks, target_level, assumptions)
            cooldown = spell.cooldown + sum(
                e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                for e in t.effects if e.kind == "cooldown" and name in e.applies_to)
            period = spell.duration if kind == "dots" else max(cooldown, seconds)
            if ev <= 0 or period <= 0 or time_left <= seconds / period:
                continue
            time_left -= seconds / period
            dps += ev / period
            mana += cost / period
            used.append(name)

    best = None
    for name in plan["fillers"]:
        spell = learned(name)
        if spell is None:
            continue
        ev, seconds, cost = cast(spell, stats, cls, ranks, target_level, assumptions)
        if ev > 0 and (best is None or ev / seconds > best[0] / best[1]):
            best = (ev, seconds, cost, name)
    if best is not None:
        dps += time_left * best[0] / best[1]
        mana += time_left * best[2] / best[1]
        used.append(best[3])

    regen = regen_while_casting(class_name, stats, cls, ranks)
    return CasterRotation(dps=dps, mana_per_second=mana - regen, regen_per_second=regen, spells=tuple(used))
