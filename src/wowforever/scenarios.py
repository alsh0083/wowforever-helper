"""v0 PvE scenarios (#19): questing kills/hour, AoE break-even, sustained raid DPS.

Each scenario scores one character at one level under a single activity. Formulas are
fixed by the hand-worked golden values in `tests/test_scenarios.py`; default parameters
come from `config/scenarios.toml`.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from wowforever.assumptions import Assumptions, periodic_can_crit
from wowforever.calc.ev import effective_cast_time, expected_damage
from wowforever.schema import ClassData, SpellRank
from wowforever.stats import Stats

from wowforever.calc.talents import modifiers_for


CONFIG = Path(__file__).resolve().parents[2] / "config" / "scenarios.toml"


@dataclass(frozen=True)
class Character:
    """One character at one level: stats, learned spell ranks, and taken talents."""

    level: int
    stats: Stats
    spells: tuple[SpellRank, ...]
    cls: ClassData
    ranks: Mapping[int, int]  # talent id -> rank


@dataclass(frozen=True)
class QuestingParams:
    mob_hp: float
    travel_seconds: float
    drink_mana_per_second: float
    fillers: tuple[str, ...]


@dataclass(frozen=True)
class AoeParams:
    mob_hp: float
    pack_sizes: tuple[int, ...]
    aoe_spells: tuple[str, ...]
    fillers: tuple[str, ...]


@dataclass(frozen=True)
class RaidParams:
    fight_seconds: float
    mana_per_second: float
    fillers: tuple[str, ...]
    target_level_offset: int = 3
    extra_mana: float = 0.0  # Evocation, mana gems, potions over the fight


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    level: int
    score: float
    unit: str
    details: dict[str, Any]
    assumptions: dict[str, Any]


def scaled(spell: SpellRank, caster_level: int) -> SpellRank:
    """Base damage of `spell` at `caster_level`, adding per-level scaling up to its cap."""
    if spell.damage_per_level <= 0:
        return spell
    levels = max(0, min(caster_level, spell.scaling_max_level) - spell.level)
    bonus = spell.damage_per_level * levels
    return replace(spell, min_damage=spell.min_damage + bonus, max_damage=spell.max_damage + bonus)


def best_rank(spells: Sequence[SpellRank], name: str, level: int) -> SpellRank | None:
    """Highest-rank spell named `name` learned at or below `level`."""
    learned = [s for s in spells if s.name == name and s.level <= level]
    return max(learned, key=lambda s: s.rank) if learned else None


def _cast(char: Character, spell: SpellRank, target_level: int,
          assumptions: Assumptions) -> tuple[float, float, float]:
    """(EV per cast, seconds per cast, mana cost) of `spell` on a `target_level` target.

    Seconds per cast is the cast time, stretched to the full duration for channels and to the
    cooldown for spells that can't be recast sooner."""
    mods = modifiers_for(spell, char.cls, char.ranks)

    def ev_of(s: SpellRank) -> float:
        return expected_damage(
            scaled(s, char.level),
            spell_power=char.stats.spell_power,
            crit_pct=char.stats.crit_pct,
            hit_pct=char.stats.hit_pct,
            caster_level=char.level,
            target_level=target_level,
            mods=mods,
            periodic_can_crit=periodic_can_crit(spell.name, assumptions),
        )

    ev = ev_of(spell)
    cast = effective_cast_time(spell, mods)
    if spell.channeled:
        cast = max(cast, spell.duration)
    # v0 repeats one spell, so a cooldown caps how often it can be cast (rotations come in v1)
    cast = max(cast, spell.cooldown)
    # recasting refreshes a DoT instead of stacking it: a repeat only gains the part of the
    # periodic damage that ticks before the next cast
    if not spell.channeled and spell.duration > cast and (spell.periodic_damage or spell.periodic_coefficient):
        direct = ev_of(replace(spell, periodic_damage=0.0, periodic_coefficient=0.0))
        ev = direct + (ev - direct) * cast / spell.duration
    cost = spell.mana_cost * (1 + mods.mana_cost_pct / 100)
    return ev, cast, cost


def _best_of(char: Character, names: Sequence[str], target_level: int,
             assumptions: Assumptions, what: str) -> SpellRank:
    """Spell with the highest expected damage per second among `names` learned by level."""
    best: SpellRank | None = None
    best_dps = -1.0
    for name in names:
        spell = best_rank(char.spells, name, char.level)
        if spell is None:
            continue
        ev, cast, _ = _cast(char, spell, target_level, assumptions)
        if ev <= 0:  # no modeled damage (e.g. a spell whose damage lives in an unmodeled trigger)
            continue
        if ev / cast > best_dps:
            best, best_dps = spell, ev / cast
    if best is None:
        raise ValueError(f"no {what} available at level {char.level}")
    return best


def questing(char: Character, p: QuestingParams, assumptions: Assumptions) -> ScenarioResult:
    """Kills/hour while questing: kill time + drink downtime + travel, per kill."""
    spell = _best_of(char, p.fillers, char.level, assumptions, "filler")
    rot = _rotation(char, spell, char.level, assumptions, sustained=False)
    time_to_kill = p.mob_hp / rot.dps
    mana_per_kill = p.mob_hp / rot.dps * rot.mana_per_second
    downtime = mana_per_kill / p.drink_mana_per_second
    return ScenarioResult(
        scenario="questing",
        level=char.level,
        score=3600 / (time_to_kill + downtime + p.travel_seconds),
        unit="kills/hour",
        details={"spell": spell.name, "time_to_kill": time_to_kill,
                 "mana_per_kill": mana_per_kill, "downtime": downtime},
        assumptions=assumptions.describe(),
    )


def aoe_curve(char: Character, p: AoeParams, assumptions: Assumptions) -> ScenarioResult:
    """AoE vs single-target kill times per pack size, and the break-even pack."""
    aoe = _best_of(char, p.aoe_spells, char.level, assumptions, "AoE spell")
    ev, cast, _ = _cast(char, aoe, char.level, assumptions)
    per_mob_dps = ev / cast
    single = _best_of(char, p.fillers, char.level, assumptions, "filler")
    se, scast, _ = _cast(char, single, char.level, assumptions)
    time_to_kill = p.mob_hp / (se / scast)
    capped = assumptions["aoe_target_cap"] == "soft_4"
    aoe_time: dict[int, float] = {}
    single_time: dict[int, float] = {}
    for n in p.pack_sizes:
        per_mob = per_mob_dps * min(n, 4) / n if capped else per_mob_dps
        aoe_time[n] = p.mob_hp / per_mob
        single_time[n] = n * time_to_kill
    break_even = next((n for n in p.pack_sizes if aoe_time[n] < single_time[n]), None)
    return ScenarioResult(
        scenario="aoe",
        level=char.level,
        score=float(break_even or 0),
        unit="pack size",
        details={"aoe_spell": aoe.name, "aoe_time": aoe_time,
                 "single_time": single_time, "break_even": break_even},
        assumptions=assumptions.describe(),
    )


def raid(char: Character, p: RaidParams, assumptions: Assumptions) -> ScenarioResult:
    """Sustained DPS in a raid fight, cut short if the character runs out of mana."""
    target = char.level + p.target_level_offset
    spell = _best_of(char, p.fillers, target, assumptions, "filler")
    rot = _rotation(char, spell, target, assumptions, sustained=True)
    dps = rot.dps
    drain = rot.mana_per_second - p.mana_per_second
    if drain <= 0:
        time_to_oom: float | None = None
        score = dps
    else:
        time_to_oom = (char.stats.mana + p.extra_mana) / drain
        score = dps * min(1, time_to_oom / p.fight_seconds)
    return ScenarioResult(
        scenario="raid",
        level=char.level,
        score=score,
        unit="dps",
        details={"spell": spell.name, "dps": rot.dps, "time_to_oom": time_to_oom},
        assumptions=assumptions.describe(),
    )


def _rotation(char: Character, spell: SpellRank, target_level: int,
              assumptions: Assumptions, *, sustained: bool):
    """The class's rotation model (#57); imported here to avoid an import cycle."""
    from wowforever.classes.mage_rotation import rotation

    return rotation(char, spell, target_level=target_level, assumptions=assumptions,
                    sustained=sustained)


def default_params(scenario: str, level: int) -> QuestingParams | AoeParams | RaidParams:
    """Default parameters for a scenario at `level`, from config/scenarios.toml."""
    raw = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    fillers = tuple(raw["fillers"])
    if scenario == "questing":
        section = raw["questing"]
        mob_hp, drink = _anchor_at(section["anchors"], level)
        return QuestingParams(mob_hp=mob_hp, travel_seconds=section["travel_seconds"],
                              drink_mana_per_second=drink, fillers=fillers)
    if scenario == "aoe":
        mob_hp, _ = _anchor_at(raw["questing"]["anchors"], level)
        return AoeParams(mob_hp=mob_hp, pack_sizes=tuple(raw["aoe"]["pack_sizes"]),
                         aoe_spells=tuple(raw["aoe_spells"]), fillers=fillers)
    if scenario == "raid":
        section = raw["raid"]
        return RaidParams(fight_seconds=section["fight_seconds"],
                          mana_per_second=section["mana_per_second"],
                          fillers=fillers,
                          target_level_offset=section.get("target_level_offset", 3),
                          extra_mana=section.get("extra_mana", 0.0))
    raise ValueError(f"unknown scenario {scenario!r}")


def _anchor_at(raw_anchors: Mapping[str, Sequence[float]], level: int) -> list[float]:
    """Anchor values at `level`, linearly interpolated and clamped at the ends.

    TOML table keys are strings, so the level keys are converted to ints first."""
    anchors = {int(k): v for k, v in raw_anchors.items()}
    levels = sorted(anchors)
    if level in anchors:
        return list(anchors[level])
    if level <= levels[0]:
        return list(anchors[levels[0]])
    if level >= levels[-1]:
        return list(anchors[levels[-1]])
    lo = max(l for l in levels if l <= level)
    hi = min(l for l in levels if l >= level)
    t = (level - lo) / (hi - lo)
    return [a + t * (b - a) for a, b in zip(anchors[lo], anchors[hi])]
