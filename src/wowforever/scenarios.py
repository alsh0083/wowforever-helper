"""v0 PvE scenarios (#19): questing kills/hour, AoE break-even, sustained raid DPS.

Each scenario scores one character at one level under a single activity. Formulas are
fixed by the hand-worked golden values in `tests/test_scenarios.py`; default parameters
come from `config/scenarios.toml`.
"""

from __future__ import annotations

import functools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from wowforever.assumptions import Assumptions, periodic_can_crit, sub20_penalized
from wowforever.calc.ev import effective_cast_time, expected_damage
from wowforever.schema import ClassData, SpellRank
from wowforever.stats import Stats

from wowforever.calc.talents import modifiers_for
from wowforever.toml_cache import load_toml


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
    extra_mana: float = 0.0  # one-off mana per fight (mana gem)
    fight_lengths: tuple[tuple[float, float], ...] = ()  # (seconds, weight); empty -> fight_seconds only
    consumables: tuple[tuple[float, float], ...] = ()    # (mana, cooldown seconds), used ceil(T / cooldown) times
    spirit_regen: bool = False      # spirit regen while casting (Arcane Meditation share) and Evocation's refill
    evocation: bool = False
    evocation_seconds: float = 8.0
    evocation_regen_pct: float = 1500.0
    fallback: bool = False          # after OOM keep casting at the mana-limited rate instead of 0 DPS


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    level: int
    score: float
    unit: str
    details: dict[str, Any]
    assumptions: dict[str, Any]


@functools.lru_cache(maxsize=None)
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
            sub20_penalized(scaled(s, char.level), assumptions),
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


def usable_fillers(char: Character, names: Sequence[str], target_level: int,
                   assumptions: Assumptions) -> list[SpellRank]:
    """The best learned rank of each of `names` that has modeled damage, in `names` order."""
    return [spell for name in names
            if (spell := best_rank(char.spells, name, char.level)) is not None
            and _cast(char, spell, target_level, assumptions)[0] > 0]


def _best_result(char: Character, names: Sequence[str], target_level: int,
                 assumptions: Assumptions, run) -> ScenarioResult:
    """The scenario result of the filler that scores best in it: `run(spell)` scores one filler,
    so weaves, procs, freezes and mana all count toward the choice."""
    results = [run(spell) for spell in usable_fillers(char, names, target_level, assumptions)]
    if not results:
        raise ValueError(f"no filler available at level {char.level}")
    return max(results, key=lambda r: r.score)


def questing(char: Character, p: QuestingParams, assumptions: Assumptions) -> ScenarioResult:
    """Kills/hour while questing with the filler that kills fastest overall."""
    return _best_result(char, p.fillers, char.level, assumptions,
                        lambda spell: _questing_with(char, spell, p, assumptions))


def _questing_with(char: Character, spell: SpellRank, p: QuestingParams,
                   assumptions: Assumptions) -> ScenarioResult:
    """Kills/hour with one filler: kill time + drink downtime + travel, per kill."""
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


def spirit_regen(stats: Stats) -> float:
    """Mana per second outside the five-second rule: Classic mage formula (13 + spirit/4) per 2 s tick."""
    return (13 + stats.spirit / 4) / 2


def combat_regen(char: Character, p: RaidParams) -> float:
    """Mana per second while casting: flat income plus the talented share of spirit regen."""
    regen = p.mana_per_second
    if p.spirit_regen:
        share = 0.0
        for talent in char.cls.talents:
            rank = char.ranks.get(talent.talent_id, 0)
            if rank <= 0:
                continue
            for effect in talent.effects:
                if effect.kind == "regen_while_casting":
                    share += effect.values[rank - 1]
        regen += spirit_regen(char.stats) * share / 100
    return regen


def _fallback(char: Character, p: RaidParams, filler: SpellRank, target: int,
              assumptions: Assumptions, income: float) -> tuple[float, SpellRank | None]:
    """Best mana-limited DPS once dry: every learned rank of the filler plus the best rank of each
    other filler, each throttled to what `income` can pay for."""
    candidates = [s for s in char.spells
                  if s.name == filler.name and s.level <= char.level]
    for name in p.fillers:
        if name != filler.name:
            other = best_rank(char.spells, name, char.level)
            if other is not None:
                candidates.append(other)
    best, best_dps = None, 0.0
    for spell in candidates:
        rot = _rotation(char, spell, target, assumptions, sustained=True)
        if rot.dps <= 0:
            continue
        dps = rot.dps * (min(1.0, income / rot.mana_per_second) if rot.mana_per_second > 0 else 1.0)
        if dps > best_dps:
            best, best_dps = spell, dps
    return best_dps, best


def raid(char: Character, p: RaidParams, assumptions: Assumptions) -> ScenarioResult:
    """Sustained DPS over a mix of fight lengths with a mana budget (#78).

    Budget per fight: mana pool + one-off mana + consumables once per cooldown + Evocation when the
    build would otherwise run dry (it costs its channel time). Once dry, the mage keeps casting at
    the rate combat regen pays for (fallback), or stops when fallback is off. The filler is the one
    with the best sustained score, so a cheaper spell can beat a hungrier one."""
    target = char.level + p.target_level_offset
    return _best_result(char, p.fillers, target, assumptions,
                        lambda spell: _raid_with(char, spell, p, assumptions))


def _raid_with(char: Character, spell: SpellRank, p: RaidParams,
               assumptions: Assumptions) -> ScenarioResult:
    """Sustained raid score with one filler."""
    target = char.level + p.target_level_offset
    rot = _rotation(char, spell, target, assumptions, sustained=True)
    dps = rot.dps
    income = combat_regen(char, p)
    drain = rot.mana_per_second - income
    fallback_dps, fallback_spell = (_fallback(char, p, spell, target, assumptions, income)
                                    if p.fallback and drain > 0 else (0.0, None))

    def one_fight(seconds: float) -> tuple[float, float | None, bool]:
        """(score, time to OOM incl. Evocation channel or None, Evocation used)."""
        if drain <= 0:
            return dps, None, False
        budget = char.stats.mana + p.extra_mana + sum(
            mana * math.ceil(seconds / cooldown) for mana, cooldown in p.consumables)
        active, evocation = seconds, False
        if p.evocation and budget / drain < seconds:
            budget += spirit_regen(char.stats) * (1 + p.evocation_regen_pct / 100) * p.evocation_seconds
            active, evocation = seconds - p.evocation_seconds, True
        dry = budget / drain
        t_full = min(active, dry)
        score = (dps * t_full + fallback_dps * (active - t_full)) / seconds
        oom = dry + (p.evocation_seconds if evocation else 0.0) if dry < active else None
        return score, oom, evocation

    lengths = p.fight_lengths or ((p.fight_seconds, 1.0),)
    by_length = {seconds: one_fight(seconds)[0] for seconds, _ in lengths}
    score = sum(by_length[s] * w for s, w in lengths) / sum(w for _, w in lengths)
    _, time_to_oom, evocation_used = one_fight(p.fight_seconds)
    return ScenarioResult(
        scenario="raid",
        level=char.level,
        score=score,
        unit="dps",
        details={"spell": spell.name, "dps": dps, "time_to_oom": time_to_oom,
                 "evocation_used": evocation_used,
                 "fallback_spell": f"{fallback_spell.name} rank {fallback_spell.rank}" if fallback_spell else None,
                 "by_length": by_length},
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
    raw = load_toml(CONFIG)
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
    if scenario in ("raid", "dungeon"):
        section = raw[scenario]
        return RaidParams(fight_seconds=section["fight_seconds"],
                          mana_per_second=section["mana_per_second"],
                          fillers=fillers,
                          target_level_offset=section.get("target_level_offset", 3),
                          extra_mana=section.get("extra_mana", 0.0),
                          fight_lengths=tuple(tuple(x) for x in section.get("fight_lengths", ())),
                          consumables=tuple(tuple(x) for x in section.get("consumables", ())),
                          spirit_regen=section.get("spirit_regen", False),
                          evocation=section.get("evocation", False),
                          fallback=section.get("fallback", False))
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
