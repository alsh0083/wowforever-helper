"""Rogue, hunter and warrior PvP scores (#134, #162): the mage's duel model (#26, #121) from their side.

The class's side has the same fields as the mage's: health, rotation DPS against player armor, and
what its controls do to the opponent (stuns keep a melee opponent from hitting, interrupts lock a
caster, slows help kiting). Its own controls get the same energy budget and diminishing returns as
opponent kits (config/pvp_self.toml). The score is the mean over the four world-PvP scenarios.

Opponent kits' DPS assumes cloth; physical kits hit these classes by their armor ratio.
Thorns returns damage to melee opponents (#265).
Druids heal themselves with HoTs, Swiftmend and direct heals when that helps (#265, #279).
Not modeled yet: openers from stealth, Evasion, Vanish, Deterrence and Feign Death.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from wowforever.assumptions import Assumptions
from wowforever.calc.ev import BASE_CRIT_BONUS_PCT, GCD_SECONDS
from wowforever.focus import PVP_SCENARIOS
from wowforever.classes import engine
from wowforever.melee_scenarios import build_stats
from wowforever.melee_stats import MeleeStats
from wowforever.physical import Target, armor_factor
from wowforever.pvp.duel import Control, Kit, Side, lockout_seconds, outnumbered_scores, scenario_scores
from wowforever.scenarios import best_rank
from wowforever.schema import ClassData, SpellRank
from wowforever.toml_cache import load_toml

CONFIG = Path(__file__).resolve().parents[3] / "config" / "pvp_self.toml"
STOPS_ATTACKS = ("stun", "incapacitate", "disorient", "fear")


def thorns_dps(thorns: SpellRank | None, spell_power: float, coefficient: float, hits_per_second: float) -> float:
    """Damage per second Thorns returns to a melee attacker (#265): (base + coefficient x spell power) per hit."""
    if thorns is None or thorns.damage_shield <= 0:
        return 0.0
    return (thorns.damage_shield + coefficient * spell_power) * hits_per_second


@dataclass(frozen=True)
class HealMods:
    """Talent changes to one heal (#276, #279)."""

    cast: float = 0.0          # cast time change, s
    cost: float = 0.0          # mana cost change, %
    direct_pct: float = 0.0    # more direct healing, %
    periodic_pct: float = 0.0  # more periodic healing, %
    duration: float = 0.0      # longer HoT, s
    gcd: float = 0.0           # global cooldown change, s
    crit: float = 0.0          # more crit chance, percentage points


def heal_modifiers(spell: SpellRank, cls: ClassData, ranks: Mapping[int, int]) -> HealMods:
    """Talent changes to one heal (#276, #279).

    Healing % applies to both parts when it targets "all" or the heal by name, and to the periodic part only
    when it targets "periodic" (Genesis). Cast time, mana cost, duration and global cooldown come only from
    effects naming the heal (Moonglow's school-wide cut is for damaging spells). Crit chance comes from effects
    targeting "all" or the heal by name."""
    totals = dict.fromkeys(("cast", "cost", "direct_pct", "periodic_pct", "duration", "gcd", "crit"), 0.0)
    named = {"cast_time": "cast", "mana_cost_pct": "cost", "duration": "duration", "gcd": "gcd"}
    for talent_id, rank in ranks.items():
        if rank <= 0:
            continue
        for effect in cls.talent(talent_id).effects:
            value = effect.values[rank - 1]
            if effect.kind == "healing_pct":
                if "all" in effect.applies_to or spell.name in effect.applies_to:
                    totals["direct_pct"] += value
                    totals["periodic_pct"] += value
                elif "periodic" in effect.applies_to:
                    totals["periodic_pct"] += value
            elif effect.kind == "crit_chance" and ("all" in effect.applies_to or spell.name in effect.applies_to):
                totals["crit"] += value
            elif effect.kind in named and spell.name in effect.applies_to:
                totals[named[effect.kind]] += value
    return HealMods(**totals)


def _heal(spell: SpellRank, spell_power: float, mods: HealMods, crit_pct: float) -> tuple[float, float, float, float]:
    """(direct healing, periodic healing, seconds, mana) of one cast after talents; direct healing crits (#283)."""
    crit = min(100.0, crit_pct + mods.crit) / 100
    direct = (((spell.heal_min + spell.heal_max) / 2 + spell.heal_coefficient * spell_power) * (1 + mods.direct_pct / 100)
              * (1 + crit * BASE_CRIT_BONUS_PCT / 100))
    periodic = 0.0
    if spell.periodic_heal > 0 and spell.duration > 0:
        periodic = ((spell.periodic_heal + spell.periodic_heal_coefficient * spell_power)
                    * (1 + mods.periodic_pct / 100) * (spell.duration + mods.duration) / spell.duration)
    seconds = max(GCD_SECONDS + mods.gcd, spell.cast_time + mods.cast)
    return direct, periodic, seconds, spell.mana_cost * (1 + mods.cost / 100)


def heal_capacity(class_name: str, stats, spells: Sequence[SpellRank], cls: ClassData,
                  ranks: Mapping[int, int], *, assumptions: Assumptions | None = None) -> tuple[float, float]:
    """(healing per second while healing, mana-limited healing budget) for the class's healing phase (#265, #279).

    The phase opens with each heal in config `hots` once (direct part plus its full periodic healing: fights
    outlast the HoTs), then `hot_burst` (copies the biggest HoT's periodic healing; nothing when the
    swiftmend_consumes_hot assumption is on). The rest of mana x heal_mana_share goes to the heal in `heals`
    with the most direct healing per second. If the opening costs more than that mana, it scales down to fit.
    Direct healing crits at the row's crit plus crit talents (#283).
    A spell named like a talent counts only when the talent is taken. Classes without `heals`: (0, 0)."""
    cfg = load_toml(CONFIG)[class_name]
    if "heals" not in cfg:
        return (0.0, 0.0)
    if assumptions is None:
        assumptions = Assumptions.load()
    row = build_stats(class_name, stats, cls, ranks)
    sp = getattr(row, "spell_power", 0.0)
    # a melee row's crit is melee crit; its spell crit isn't modeled (#283)
    crit_pct = getattr(row, "crit_pct", 0.0) if hasattr(row, "spell_power") else 0.0
    mana_budget = row.mana * cfg["heal_mana_share"]
    talents = {t.name: t.talent_id for t in cls.talents}

    def learned(name: str) -> SpellRank | None:
        if name in talents and ranks.get(talents[name], 0) <= 0:
            return None
        return best_rank(spells, name, stats.level)

    amount = seconds = mana = biggest = 0.0
    for name in cfg.get("hots", []):
        spell = learned(name)
        if spell is None or spell.mana_cost <= 0 or spell.periodic_heal <= 0:
            continue
        direct, periodic, secs, cost = _heal(spell, sp, heal_modifiers(spell, cls, ranks), crit_pct)
        amount, seconds, mana = amount + direct + periodic, seconds + secs, mana + cost
        biggest = max(biggest, periodic)
    burst = learned(cfg["hot_burst"]) if "hot_burst" in cfg else None
    if burst is not None and biggest > 0 and not assumptions["swiftmend_consumes_hot"]:
        amount += biggest
        seconds += _heal(burst, sp, heal_modifiers(burst, cls, ranks), crit_pct)[2]
    if mana > 0 and mana >= mana_budget:
        return (amount / seconds, amount * mana_budget / mana)

    best: tuple[float, float, float] | None = None
    for name in cfg["heals"]:
        spell = learned(name)
        if spell is None or spell.mana_cost <= 0 or spell.heal_max <= 0:
            continue
        direct, _, secs, cost = _heal(spell, sp, heal_modifiers(spell, cls, ranks), crit_pct)
        if best is None or direct / secs > best[0] / best[1]:
            best = (direct, secs, cost)
    if best is not None:
        filler = (mana_budget - mana) * best[0] / best[2]
        amount, seconds = amount + filler, seconds + filler * best[1] / best[0]
    return (amount / seconds, amount) if seconds > 0 else (0.0, 0.0)


def class_side(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
               ranks: Mapping[int, int], *, assumptions: Assumptions | None = None) -> Side:
    """The class's duel side, in the same shape as the mage's."""
    if assumptions is None:
        assumptions = Assumptions.load()
    raw = load_toml(CONFIG)
    cfg = raw[class_name]
    taken = {t.name for t in cls.talents if ranks.get(t.talent_id, 0) > 0}
    entries = [c for c in cfg["controls"] if c.get("requires") is None or c["requires"] in taken]
    controls = [Control(c["kind"], float(c["duration"]), float(c["cooldown"]), float(c.get("energy", 0.0)))
                for c in entries]
    locks = lockout_seconds(controls, cfg.get("energy_per_minute", 0.0))
    # controls whose spell hits several enemies (data MaxTargets > 1: Psychic Scream, Intimidating Shout)
    wide = [ctrl for ctrl, c in zip(controls, entries)
            if (spell := best_rank(spells, c["name"], stats.level)) is not None and spell.max_targets > 1]
    wide_locks = lockout_seconds(wide, cfg.get("energy_per_minute", 0.0))
    output = engine(class_name).output(stats, spells, cls, ranks, Target(0, raw["player_armor"]))
    slow = cfg.get("slow", 0.0)
    if "slow_ranged" in cfg:                    # a slow that depends on the range it fights at (hunter)
        slow = cfg["slow_ranged"] if output.ranged else cfg["slow_melee"]
    row = build_stats(class_name, stats, cls, ranks)
    thorns = thorns_dps(best_rank(spells, "Thorns", stats.level), getattr(row, "spell_power", 0.0),
                        assumptions["thorns_spell_power_coefficient"], raw.get("opponent_melee_hits_per_second", 0.0))
    heal_hps, heal_budget = heal_capacity(class_name, stats, spells, cls, ranks, assumptions=assumptions)
    # more targets for a root control from taken talents (Overgrowth, #278)
    roots = {c["name"] for c in cfg["controls"] if c["kind"] == "root"}
    extra = sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                for e in t.effects if e.kind == "targets" and roots & set(e.applies_to))
    # damage breaks roots past a share of the target's health, raised by talents (#286)
    tougher = sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                  for e in t.effects if e.kind == "break_threshold_pct" and roots & set(e.applies_to))
    root_durations = [c.duration for c in controls if c.kind == "root"]
    return Side(
        health=row.health,
        dps=output.dps,
        melee_bonus_dps=thorns,
        absorb_per_min=0.0,
        immunity_share=0.0,
        # roots don't stop casting, so lockout_seconds skips them; they're kiting time vs melee
        root=min(60.0, sum(c.duration * 60 / c.cooldown for c in controls if c.kind == "root" and c.cooldown > 0)),
        stun=sum(locks.get(kind, 0.0) for kind in STOPS_ATTACKS),
        slow=slow,
        interrupt=locks.get("interrupt", 0.0) + locks.get("silence", 0.0),
        physical_taken=(armor_factor(stats.level, raw["own_armor"][class_name])
                        / armor_factor(stats.level, raw["cloth_armor"])),
        heal_hps=heal_hps,
        heal_budget=heal_budget,
        root_targets=1 + int(extra),
        stun_aoe=min(sum(locks.get(kind, 0.0) for kind in STOPS_ATTACKS),
                     sum(wide_locks.get(kind, 0.0) for kind in STOPS_ATTACKS)),
        root_break_health=assumptions["roots_break_health_pct"] / 100 * (1 + tougher / 100),
        root_duration=max(root_durations, default=0.0),
    )


def pvp_score(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
              ranks: Mapping[int, int], kits: Sequence[Kit]) -> float:
    """Mean duel score over the four world-PvP scenarios (as the mage's, without battlegrounds)."""
    side = class_side(class_name, stats, spells, cls, ranks)
    scores = scenario_scores(side, kits)
    return sum(scores[s]["score"] for s in PVP_SCENARIOS) / len(PVP_SCENARIOS)


def outnumbered_score(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                      ranks: Mapping[int, int], kits: Sequence[Kit]) -> float:
    """Mean 2v1 score over pairs of kits (#278), a separate score next to pvp_score."""
    return outnumbered_scores(class_side(class_name, stats, spells, cls, ranks), kits)["score"]
