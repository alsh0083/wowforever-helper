"""Caster spell engine (#163): one sustained single-target rotation for any caster class.

A class declares `ROTATION = {"dots": [...], "cooldowns": [...], "fillers": [...]}` in its module:
DoTs are kept up (recast once per duration), cooldown nukes go out on cooldown, and the remaining
time goes to the filler with the best damage per second. Each cast's expected damage comes from the
mage's EV engine (`calc.ev.expected_damage`) with the class's talent modifiers, so effect rules by
school or spell name work as they do for the mage. Mana: the rotation's cost per second minus the
talented share of spirit regen while casting (config/casters.toml).

AoE pulls (#260): seconds to clear a pack with the best of the class's `aoe_spells` mixed into the
rotation, or the rotation alone.

Not modeled here: procs, cleave, pets (warlock, #165) and Life Tap; classes add those.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace

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


@dataclass(frozen=True)
class AoePull:
    seconds: float   # to clear the pack
    spell: str       # the AoE spell used, or "single target"


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
         assumptions: Assumptions, conditions: frozenset[str] = frozenset(),
         extra_damage_pct: float = 0.0) -> tuple[float, float, float]:
    """(expected damage, seconds of casting, mana) for one cast; instants take a global cooldown and
    channels their full duration. `conditions` switch on `@`-token talent rules (`dot:<name>` while that DoT is
    up) and `extra_damage_pct` adds a spell's own bonus (Lava Burst with Flame Shock, #384)."""
    mods = modifiers_for(spell, cls, ranks, conditions)
    if extra_damage_pct:
        mods = replace(mods, damage_pct=mods.damage_pct + extra_damage_pct)
    ev = expected_damage(sub20_penalized(scaled(spell, stats.level), assumptions),
                         spell_power=stats.spell_power, crit_pct=stats.crit_pct, hit_pct=stats.hit_pct,
                         caster_level=stats.level, target_level=target_level, mods=mods,
                         periodic_can_crit=periodic_can_crit(spell.name, assumptions))
    seconds = max(GCD_SECONDS, effective_cast_time(spell, mods))
    if spell.channeled:
        seconds = max(seconds, spell.duration)
    grace = sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                for e in t.effects if e.kind == "crit_haste_pct")
    if grace and not spell.channeled:
        # a crit speeds up the next cast (Nature's Grace, #397): on average by the crit chance
        seconds *= 1 - grace / 100 * min(1.0, (stats.crit_pct + mods.crit_chance_bonus) / 100)
    return ev, seconds, spell.mana_cost * (1 + mods.mana_cost_pct / 100)


def talent_stats(class_name: str, stats: Stats, cls: ClassData, ranks: Mapping[int, int]) -> Stats:
    """The build's `stat_pct` talents (Mental Strength, Dark Inspiration; 70425, #356) through the
    class's conversions, then its `spell_power_from` talents (Demonic Knowledge, Mental Quickness, #396)."""
    from wowforever.stat_weights import apply

    for talent in cls.talents:
        rank = ranks.get(talent.talent_id, 0)
        if rank <= 0:
            continue
        for effect in talent.effects:
            if effect.kind != "stat_pct":
                continue
            stat = effect.applies_to[0]
            if getattr(stats, stat, None) is None:       # Cat Form Strength on a caster row (#383)
                continue
            bumped = apply(class_name, stats, stat, getattr(stats, stat) * effect.values[rank - 1] / 100)
            if bumped is not None:
                stats = bumped
    for talent in cls.talents:
        rank = ranks.get(talent.talent_id, 0)
        for effect in (talent.effects if rank > 0 else ()):
            if effect.kind == "spell_power_from":
                base = stats.level if effect.applies_to[0] == "level" else getattr(stats, effect.applies_to[0])
                stats = replace(stats, spell_power=stats.spell_power + base * effect.values[rank - 1] / 100)
    return stats


def longer_dot(spell: SpellRank, cls: ClassData, ranks: Mapping[int, int]) -> SpellRank:
    """`spell` with its talents' extra DoT seconds (Improved Shadow Word: Pain, Call of Flame, #384): more ticks, so
    its periodic damage and coefficient grow with the duration."""
    extra = sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                for e in t.effects if e.kind == "dot_seconds" and spell.name in e.applies_to)
    if extra <= 0 or spell.duration <= 0:
        return spell
    scale = (spell.duration + extra) / spell.duration
    return replace(spell, duration=spell.duration + extra, periodic_damage=spell.periodic_damage * scale,
                   periodic_coefficient=spell.periodic_coefficient * scale)


def life_tap_pct(cls: ClassData, ranks: Mapping[int, int]) -> float:
    """Percent more mana per Life Tap from the build's talents (Improved Life Tap, #396)."""
    return sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
               for e in t.effects if e.kind == "life_tap_pct")


def consumed_period(duration: float, cooldown: float, keep_pct: float) -> float:
    """Seconds between casts of a DoT that a cooldown consumes (Conflagrate eats Immolate, #385): the DoT runs
    its full duration when kept (keep_pct%), else only until the next consuming cast."""
    keep = min(1.0, keep_pct / 100)
    return keep * duration + (1 - keep) * min(duration, cooldown)


def caster_rotation(class_name: str, stats: Stats, spells: Sequence[SpellRank], cls: ClassData,
                    ranks: Mapping[int, int], target: Target, *,
                    drink_mana_per_second: float | None = None,
                    skip: Collection[str] = ()) -> CasterRotation:
    """Sustained DPS and mana use against `target` with the class's ROTATION and talents `ranks`.

    The filler is the one with the best damage per second; with `drink_mana_per_second` (questing,
    where drinking is the bottleneck) it is the one with the best damage per second of kill time
    plus drinking, so a cheaper filler (Mind Flay over Smite) wins when mana runs out first.
    `skip` names DoTs and cooldowns to leave out (#390)."""
    stats = talent_stats(class_name, stats, cls, ranks)
    plan = class_module(class_name).ROTATION
    assumptions = Assumptions.load()
    target_level = stats.level + target.level_diff
    time_left, dps, mana, used = 1.0, 0.0, 0.0, []

    talent_ids = {t.name: t.talent_id for t in cls.talents}

    def learned(name: str) -> SpellRank | None:
        # a spell taught by a talent (Conflagrate, Lava Burst, Mind Flay) needs that talent
        if name in talent_ids and ranks.get(talent_ids[name], 0) <= 0:
            return None
        return best_rank(spells, name, stats.level)

    def cooldown_of(spell: SpellRank) -> float:
        return spell.cooldown + sum(
            e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
            for e in t.effects if e.kind == "cooldown" and spell.name in e.applies_to)

    consumers = {}   # DoT -> (seconds between the casts that consume it, % chance to keep it), #385
    for name, dot in plan.get("consumes", {}).items():
        spell = learned(name)
        if spell is None or name in skip:
            continue
        keep = sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                   for e in t.effects if e.kind == "proc_chance" and f"@keep_{dot}" in e.applies_to)
        consumers[dot] = (cooldown_of(spell), keep)

    def boosts(name: str) -> tuple[frozenset[str], float]:
        """Conditions and extra damage % for `name` from the DoTs already kept up (#384, #395)."""
        up = frozenset(f"dot:{n}" for n in used if n in plan.get("dots", ()))
        dot, pct = plan.get("dot_bonus", {}).get(name, (None, 0.0))
        return up, (pct if f"dot:{dot}" in up else 0.0)

    for kind in ("dots", "cooldowns"):
        for name in plan.get(kind, ()):
            if name in skip:
                continue
            spell = learned(name)
            if spell is None:
                continue
            if kind == "dots":
                spell = longer_dot(spell, cls, ranks)
            conditions, extra = boosts(name)
            ev, seconds, cost = cast(spell, stats, cls, ranks, target_level, assumptions, conditions, extra)
            cooldown = cooldown_of(spell)
            period = spell.duration if kind == "dots" else max(cooldown, seconds)
            if kind == "dots" and name in consumers and spell.duration > 0:
                # a consuming cooldown cuts the DoT short: only its ticks until then count (#385)
                direct, _, _ = cast(replace(spell, periodic_damage=0.0, periodic_coefficient=0.0), stats, cls,
                                    ranks, target_level, assumptions)
                period = consumed_period(spell.duration, *consumers[name])
                ev = direct + (ev - direct) * period / spell.duration
            if ev <= 0 or period <= 0 or time_left <= seconds / period:
                continue
            time_left -= seconds / period
            dps += ev / period
            mana += cost / period
            used.append(name)

    regen = regen_while_casting(class_name, stats, cls, ranks)
    regen += (caster_config(class_name).get("extra_regen_per_second", 0.0)        # Life Tap
              * (1 + life_tap_pct(cls, ranks) / 100))

    def worth(ev: float, seconds: float, cost: float) -> float:
        total_dps = dps + time_left * ev / seconds
        if drink_mana_per_second is None:
            return total_dps
        drain = max(0.0, mana + time_left * cost / seconds - regen)
        return total_dps / (1 + drain / drink_mana_per_second)

    best = None
    for name in plan["fillers"]:
        spell = learned(name)
        if spell is None:
            continue
        conditions, extra = boosts(name)
        ev, seconds, cost = cast(spell, stats, cls, ranks, target_level, assumptions, conditions, extra)
        if ev > 0 and (best is None or worth(ev, seconds, cost) > worth(*best[:3])):
            best = (ev, seconds, cost, name)
    if best is not None:
        dps += time_left * best[0] / best[1]
        mana += time_left * best[2] / best[1]
        used.append(best[3])
    return CasterRotation(dps=dps, mana_per_second=mana - regen, regen_per_second=regen, spells=tuple(used))


def chain_hits(pack: int, max_targets: int, falloff_pct: float) -> float:
    """Targets' worth of damage one cast deals to a pack (#260): every mob when max_targets is 0, else
    min(pack, max_targets) hits, each jump dealing falloff_pct% less than the one before."""
    if max_targets <= 0:
        return float(pack)
    return sum((1 - falloff_pct / 100) ** k for k in range(min(pack, max_targets)))


def pull_seconds(pack: int, mob_hp: float, single_dps: float, ev: float, seconds: float, period: float,
                 hits: float) -> float:
    """Seconds to clear `pack` mobs of `mob_hp` casting an AoE spell once per `period` (its cast time or
    cooldown, whichever is longer) and the single-target rotation in between (#260). Damage counts against
    the pack's total health; overkill and mobs dying early aren't modeled."""
    rate = ev * hits / period + (1 - seconds / period) * single_dps
    return pack * mob_hp / rate


def aoe_pull(class_name: str, stats: Stats, spells: Sequence[SpellRank], cls: ClassData,
             ranks: Mapping[int, int], pack: int, mob_hp: float, *,
             assumptions: Assumptions | None = None) -> AoePull:
    """The fastest way to clear `pack` same-level mobs of `mob_hp` (#260): each of the class's
    `aoe_spells` (config/casters.toml) mixed into the rotation, or the rotation alone. A spell taught by
    a talent needs that talent; Hellfire's damage to the caster isn't modeled."""
    if assumptions is None:
        assumptions = Assumptions.load()
    cfg = caster_config(class_name)
    single_dps = caster_rotation(class_name, stats, spells, cls, ranks, Target(0, 0)).dps
    best = AoePull(pack * mob_hp / single_dps, "single target")
    talent_ids = {t.name: t.talent_id for t in cls.talents}
    for name in cfg.get("aoe_spells", ()):
        if name in talent_ids and ranks.get(talent_ids[name], 0) <= 0:
            continue
        spell = best_rank(spells, name, stats.level)
        if spell is None:
            continue
        ev, seconds, _ = cast(spell, stats, cls, ranks, stats.level, assumptions)
        if ev <= 0:
            continue
        cooldown = spell.cooldown + sum(
            e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
            for e in t.effects if e.kind == "cooldown" and name in e.applies_to)
        hits = chain_hits(pack, cfg.get("aoe_max_targets", {}).get(name, 0), assumptions["chain_jump_falloff_pct"])
        t = pull_seconds(pack, mob_hp, single_dps, ev, seconds, max(seconds, cooldown), hits)
        if t < best.seconds:
            best = AoePull(t, name)
    return best
