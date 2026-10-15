"""World-PvP duel model (#26): an expected time-to-kill race between a mage build and an
opponent kit (docs/design/pvp-duel-model.md).

The score is a ratio of expected times - 0 the mage always loses, 0.5 even, 1 always wins -
not a win probability. Formulas are pinned by tests/test_duel.py and tests/test_duel_dr.py;
constants come from config/duel.toml and opponent kits from config/opponents/*.toml.
"""

from __future__ import annotations

import dataclasses
import functools
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wowforever.assumptions import Assumptions
from wowforever.calc.pvp_axes import control, survival
from wowforever.classes.mage_rotation import frozen_hit_gain, rotation
from wowforever.schema import SpellRank
from wowforever.scenarios import Character, best_rank

CONFIG = Path(__file__).resolve().parents[3] / "config" / "duel.toml"
OPPONENTS = Path(__file__).resolve().parents[3] / "config" / "opponents"

# Kit control kinds that stop the mage from casting. Slows and roots do not stop casting;
# they enter the duel through the mage's root/stun/slow components as kiting time.
CAST_LOCKS = frozenset({"stun", "incapacitate", "disorient", "fear", "silence", "interrupt"})
# CAST_LOCKS kinds that stack diminishing returns, one DR category each (Classic DR, #121).
DR_KINDS = frozenset({"stun", "incapacitate", "disorient", "fear"})

_CONFIG: dict[str, Any] | None = None


def _config() -> dict[str, Any]:
    """The duel constants, read once per process."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    return _CONFIG


@dataclass(frozen=True)
class Control:
    """One control the opponent can land on the mage; seconds, 0 cooldown = on demand."""

    kind: str
    duration: float
    cooldown: float
    energy: float = 0.0  # energy per use; 0 = not energy-limited


@dataclass(frozen=True)
class Kit:
    """An opposing class/spec at the mage's level: stats, controls, removals, immunity."""

    id: str
    role: str  # melee | ranged | caster
    stealth: bool
    dispels_buffs: bool
    health: float
    dps: float
    opener_damage: float
    opener_stun: float
    controls: tuple[Control, ...]
    removes: tuple[tuple[str, float], ...]  # (comma-separated kinds removed, cooldown)
    immunity: tuple[float, float] | None  # (duration, cooldown) seconds
    energy_per_minute: float = 0.0  # energy per minute; 0 = no energy budget
    at_level: int = 60  # level its health/DPS describe; 60 = config values (#272)


@dataclass(frozen=True)
class Side:
    """The mage's side of a duel: health, DPS and control in seconds per minute."""

    health: float
    dps: float
    absorb_per_min: float  # Ice Barrier absorb per minute
    immunity_share: float  # share of the fight spent immune (Ice Block + Cold Snap)
    root: float
    stun: float
    slow: float  # uptime x strength, 0-1
    interrupt: float
    melee_bonus_dps: float = 0.0  # extra DPS against melee: one frozen hit per Frost Nova (#97)
    physical_taken: float = 1.0  # physical damage taken vs the cloth that kit DPS assumes (#134)
    heal_hps: float = 0.0  # healing per second while casting heals (#265)
    heal_budget: float = 0.0  # mana-limited healing for the fight
    root_targets: int = 1  # opponents its roots hold at once (Overgrowth, #278)
    root_break_health: float = 0.0  # damage that breaks its root, share of the target's health; 0 = never (#286)
    root_duration: float = 0.0  # seconds one root lasts unbroken
    stun_aoe: float = 0.0  # the part of `stun` from controls that hit every nearby enemy (#287)


@dataclass(frozen=True)
class DuelResult:
    """One duel: expected kill times in seconds and the score (0-1, 0.5 even)."""

    score: float
    t_side: float
    t_opponent: float
    side_uptime: float
    opponent_uptime: float


def _config_kits(directory: Path) -> list[Kit]:
    """Every opponent kit in `directory`, sorted by id."""
    kits: list[Kit] = []
    for path in directory.glob("*.toml"):
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        at_60 = raw["at_60"]
        immunity = raw.get("immunity")
        kits.append(Kit(
            id=raw["id"],
            role=raw["role"],
            stealth=bool(raw["stealth"]),
            dispels_buffs=bool(raw["dispels_buffs"]),
            health=float(at_60["health"]),
            dps=float(at_60["dps"]),
            opener_damage=float(at_60["opener_damage"]),
            opener_stun=float(at_60["opener_stun"]),
            controls=tuple(
                Control(kind=c["kind"], duration=float(c["duration"]),
                        cooldown=float(c["cooldown"]), energy=float(c.get("energy", 0.0)))
                for c in raw.get("controls", ())
            ),
            removes=tuple((r["removes"], float(r["cooldown"])) for r in raw.get("removes", ())),
            immunity=(float(immunity["duration"]), float(immunity["cooldown"])) if immunity else None,
            energy_per_minute=float(at_60.get("energy_per_minute", 0.0)),
        ))
    return sorted(kits, key=lambda kit: kit.id)


@functools.lru_cache(maxsize=None)
def _kits_at(directory: Path, level: int) -> tuple[Kit, ...]:
    kits = _config_kits(directory)
    if level == 60:
        return tuple(kits)
    from wowforever.pvp.kit_stats import KIT_BUILDS, engine_at   # lazy: kit_stats runs the engines
    out = []
    for kit in kits:
        if kit.id not in KIT_BUILDS:
            out.append(kit)            # no engine build (the mage kit): level-60 values, at_level stays 60
            continue
        h, d = engine_at(kit.id, level)
        h60, d60 = engine_at(kit.id, 60)
        out.append(dataclasses.replace(kit, health=kit.health * h / h60, dps=kit.dps * d / d60,
                                       opener_damage=kit.opener_damage * d / d60, at_level=level))
    return tuple(out)


def load_kits(level: int = 60, directory: Path = OPPONENTS) -> list[Kit]:
    """Every opponent kit in `directory`, sorted by id, at `level` (#272): config values at 60,
    engine kits scaled by their level / 60 engine ratio below it."""
    return list(_kits_at(directory, level))


def root_hold(side: Side, kit: Kit) -> float:
    """Share of the side's root time that holds on `kit` while the side damages it (#286): the root breaks
    once the side has dealt root_break_health x kit health. 1 when the side's roots don't break."""
    if side.root_break_health <= 0 or side.root_duration <= 0 or side.dps <= 0:
        return 1.0
    return min(1.0, side.root_break_health * kit.health / (side.dps * side.root_duration))


def _held(side: Side, kit: Kit) -> Side:
    """`side` with its roots scaled by root_hold against `kit`, the target it's damaging."""
    return dataclasses.replace(side, root=side.root * root_hold(side, kit))


def _kiting_seconds(mage: Side, kit: Kit, c: dict[str, Any]) -> float:
    """Per-minute seconds the opponent cannot hit the mage, by its role."""
    if kit.role == "melee":
        kiting = mage.root + mage.stun + mage.slow * c["slow_kite_seconds"]
        cheap_removal = any(
            "slow" in kinds or "root" in kinds
            for kinds, cooldown in ((r.split(","), cooldown) for r, cooldown in kit.removes)
            if cooldown <= c["removal_max_cooldown"]
        )
        if cheap_removal:
            kiting *= c["removal_factor"]
    elif kit.role == "ranged":
        kiting = mage.stun + mage.root * c["ranged_root_share"]
    else:  # casters keep casting through slows and roots
        kiting = mage.interrupt + mage.stun
    return kiting


def lockout_seconds(controls: Sequence[Control], energy_per_minute: float = 0.0) -> dict[str, float]:
    """Seconds per minute each kind of cast-locking control keeps its target locked (#121).

    With an energy budget, controls spend at most max_control_energy_share of it and every rate
    scales down to fit. Each DR kind (stun, incapacitate, disorient, fear) is capped at
    60 * dr_chain * d / (dr_chain * d + dr_immune_seconds) for its longest control d; interrupts
    and silences aren't capped. Cooldown-0 controls (openers) don't count."""
    c = _config()
    spend = sum(ctrl.energy * 60 / ctrl.cooldown for ctrl in controls if ctrl.cooldown > 0)
    f = min(1.0, energy_per_minute * c["max_control_energy_share"] / spend) if energy_per_minute > 0 and spend > 0 else 1.0
    out: dict[str, float] = {}
    for ctrl in controls:
        if ctrl.cooldown <= 0 or ctrl.kind not in CAST_LOCKS:
            continue
        out[ctrl.kind] = out.get(ctrl.kind, 0.0) + ctrl.duration * 60 / ctrl.cooldown * f
    for kind in DR_KINDS & set(out):
        longest = max(ctrl.duration for ctrl in controls if ctrl.kind == kind)
        cap = 60 * c["dr_chain"] * longest / (c["dr_chain"] * longest + c["dr_immune_seconds"])
        out[kind] = min(out[kind], cap)
    return out


def duel(mage: Side, kit: Kit, variant: str) -> DuelResult:
    """The expected-kill race between `mage` and `kit`.

    `variant` is "mage_sees" (the mage reacts first) or "they_open" (the opponent gets its
    burst opener and opening stun before the mage acts)."""
    c = _config()
    max_fight = c["max_fight"]

    lockout = sum(lockout_seconds(kit.controls, kit.energy_per_minute).values())
    side_uptime = max(c["min_uptime"], 1 - lockout / 60)
    opponent_uptime = max(c["min_uptime"], 1 - _kiting_seconds(_held(mage, kit), kit, c) / 60)

    immune_share = kit.immunity[0] / kit.immunity[1] if kit.immunity else 0.0
    dps = mage.dps + (mage.melee_bonus_dps if kit.role == "melee" else 0.0)  # Nova needs them in melee
    t_side = kit.health / (dps * side_uptime * (1 - immune_share))

    barrier = mage.absorb_per_min / 60
    if kit.dispels_buffs:
        barrier *= c["dispel_barrier_factor"]
    physical = mage.physical_taken if kit.role in ("melee", "ranged") else 1.0
    opponent_dps = kit.dps * physical * opponent_uptime * (1 - mage.immunity_share)

    opening = kit.opener_damage + kit.opener_stun * kit.dps if variant == "they_open" else 0.0
    net = opponent_dps - barrier
    t_opponent = (mage.health - opening) / net if net > 0 else max_fight

    t_side = min(max(t_side, 0.0), max_fight)
    t_opponent = min(max(t_opponent, 0.0), max_fight)
    score = 0.5 if t_side + t_opponent == 0 else t_opponent / (t_side + t_opponent)
    if mage.heal_budget > 0 and mage.heal_hps > 0 and net > 0:
        # healing adds effective health but pauses damage (#265); heal only if the score rises.
        # Roots hold fully while healing (#290): the fight's damage rate is the time-weighted mean.
        heal_time = mage.heal_budget / mage.heal_hps
        held = max(c["min_uptime"], 1 - _kiting_seconds(mage, kit, c) / 60)
        net_heal = kit.dps * physical * held * (1 - mage.immunity_share) - barrier
        mean_net = (net * t_side + net_heal * heal_time) / (t_side + heal_time)
        h_mage = min(t_side + heal_time, max_fight)
        h_opp = min((mage.health - opening + mage.heal_budget) / mean_net, max_fight)
        h_score = h_opp / (h_mage + h_opp)
        if h_score > score:
            t_side, t_opponent, score = h_mage, h_opp, h_score
    return DuelResult(score=score, t_side=t_side, t_opponent=t_opponent,
                      side_uptime=side_uptime, opponent_uptime=opponent_uptime)


def scenario_scores(mage: Side, kits: Sequence[Kit]) -> dict[str, dict[str, Any]]:
    """Mean duel score per world-PvP scenario, with the per-kit matchup behind each mean."""
    groups: dict[str, tuple[list[Kit], str]] = {
        "wpvp_melee": ([k for k in kits if k.role == "melee"], "mage_sees"),
        "wpvp_melee_they_open": ([k for k in kits if k.role == "melee"], "they_open"),
        "wpvp_caster": ([k for k in kits if k.role in ("caster", "ranged")], "mage_sees"),
        "stealth_ambush": ([k for k in kits if k.stealth], "they_open"),
    }
    scores: dict[str, dict[str, Any]] = {}
    for name, (group, variant) in groups.items():
        matchups = {k.id: duel(mage, k, variant).score for k in group}
        scores[name] = {
            "score": sum(matchups.values()) / len(matchups) if matchups else 0.5,
            "matchups": matchups,
        }
    return scores


def combined_lockout(kits: Sequence[Kit]) -> float:
    """Seconds per minute several kits together keep the defender cast-locked (#278): each kind adds up
    across kits, and each DR kind is capped for the longest control of that kind in any of them."""
    c = _config()
    out: dict[str, float] = {}
    for kit in kits:
        for kind, seconds in lockout_seconds(kit.controls, kit.energy_per_minute).items():
            out[kind] = out.get(kind, 0.0) + seconds
    for kind in DR_KINDS & set(out):
        longest = max(ctrl.duration for kit in kits for ctrl in kit.controls if ctrl.kind == kind)
        out[kind] = min(out[kind], 60 * c["dr_chain"] * longest / (c["dr_chain"] * longest + c["dr_immune_seconds"]))
    return sum(out.values())


def outnumbered(side: Side, first: Kit, second: Kit) -> DuelResult:
    """The defender against two opponents at once, killing `first` then `second` (#278).

    Phase 1 (both alive): both kits' lockouts add up; the defender's stuns, slows and interrupts are
    split between them by outnumbered_control_split, except stun_aoe (multi-target controls), which
    reaches both; roots hold the opponent not being attacked, and
    the attacked one too with root_targets >= 2 until damage breaks them (#286). Phase 2: `second`
    alone, as in a duel. Healing happens in phase 1, with roots unbroken while it lasts (#290), and
    counts only if the score rises. side_uptime and opponent_uptime are phase 1's, the latter for
    `first`."""
    c = _config()
    max_fight = c["max_fight"]

    def kill_time(kit: Kit, uptime: float) -> float:
        dps = side.dps + (side.melee_bonus_dps if kit.role == "melee" else 0.0)
        immune = kit.immunity[0] / kit.immunity[1] if kit.immunity else 0.0
        return kit.health / (dps * uptime * (1 - immune))

    def incoming(kit: Kit, control: Side) -> tuple[float, float]:
        uptime = max(c["min_uptime"], 1 - _kiting_seconds(control, kit, c) / 60)
        physical = side.physical_taken if kit.role in ("melee", "ranged") else 1.0
        return kit.dps * physical * uptime * (1 - side.immunity_share), uptime

    def barrier(kits: Sequence[Kit]) -> float:
        b = side.absorb_per_min / 60
        return b * c["dispel_barrier_factor"] if any(k.dispels_buffs for k in kits) else b

    u1 = max(c["min_uptime"], 1 - combined_lockout([first, second]) / 60)
    u2 = max(c["min_uptime"], 1 - combined_lockout([second]) / 60)
    t1, t2 = kill_time(first, u1), kill_time(second, u2)

    split = c["outnumbered_control_split"]
    # multi-target controls (Psychic Scream, Frost Nova) reach both opponents; the rest is split (#287)
    stun = (side.stun - side.stun_aoe) * split + side.stun_aoe
    shared = dataclasses.replace(side, stun=stun, slow=side.slow * split, interrupt=side.interrupt * split)
    focus = dataclasses.replace(shared, root=side.root * root_hold(side, first) if side.root_targets >= 2 else 0.0)
    d_first, first_uptime = incoming(first, focus)
    net1 = d_first + incoming(second, shared)[0] - barrier([first, second])
    # while healing nobody is attacked, so the focus keeps a full root (#290)
    unbroken = dataclasses.replace(shared, root=side.root if side.root_targets >= 2 else 0.0)
    net1_heal = incoming(first, unbroken)[0] + incoming(second, shared)[0] - barrier([first, second])
    net2 = incoming(second, _held(side, second))[0] - barrier([second])

    def time_to_die(health: float, phase1: float, rate1: float) -> float:
        if rate1 > 0 and rate1 * phase1 >= health:
            return health / rate1
        left = health - max(rate1, 0.0) * phase1
        return phase1 + left / net2 if net2 > 0 else max_fight

    t_side = min(t1 + t2, max_fight)
    t_die = min(time_to_die(side.health, t1, net1), max_fight)
    score = t_die / (t_side + t_die)
    if side.heal_budget > 0 and side.heal_hps > 0:
        heal_time = side.heal_budget / side.heal_hps
        h_side = min(t1 + heal_time + t2, max_fight)
        rate1 = (net1 * t1 + net1_heal * heal_time) / (t1 + heal_time)
        h_die = min(time_to_die(side.health + side.heal_budget, t1 + heal_time, rate1), max_fight)
        if h_die / (h_side + h_die) > score:
            t_side, t_die, score = h_side, h_die, h_die / (h_side + h_die)
    return DuelResult(score=score, t_side=t_side, t_opponent=t_die, side_uptime=u1, opponent_uptime=first_uptime)


def outnumbered_scores(side: Side, kits: Sequence[Kit]) -> dict[str, Any]:
    """Mean outnumbered score over every pair of different kits with at least one melee kit (#278),
    each pair in its better kill order; matchups are keyed "id+id" by sorted id."""
    matchups: dict[str, float] = {}
    for i, a in enumerate(kits):
        for b in kits[i + 1:]:
            if a.id == b.id or "melee" not in (a.role, b.role):
                continue
            key = "+".join(sorted((a.id, b.id)))
            matchups[key] = max(outnumbered(side, a, b).score, outnumbered(side, b, a).score)
    return {"score": sum(matchups.values()) / len(matchups) if matchups else 0.5, "matchups": matchups}


def best_scenario_scores(char: Character, fillers: Sequence[SpellRank],
                         kits: Sequence[Kit]) -> dict[str, dict[str, Any]]:
    """Per scenario, the result of the filler that scores best in it (ties: the earlier filler),
    with that filler's name under "spell" (#97)."""
    best: dict[str, dict[str, Any]] = {}
    for filler in fillers:
        for name, result in scenario_scores(mage_side(char, filler), kits).items():
            if name not in best or result["score"] > best[name]["score"]:
                best[name] = {**result, "spell": filler.name}
    return best


def mage_side(char: Character, filler: SpellRank) -> Side:
    """The mage's duel side from a build: short-fight rotation DPS (no sustained buffs)
    plus the survival and control components."""
    s = survival(char, filler)
    c = control(char, filler)
    health = char.stats.health
    assumptions = Assumptions.load()
    nova = best_rank(char.spells, "Frost Nova", char.level)
    melee_bonus_dps = 0.0
    if nova is not None:
        improved = next((t for t in char.cls.talents if t.name == "Improved Frost Nova"), None)
        rank = char.ranks.get(improved.talent_id, 0) if improved else 0
        cut = next((e.values[rank - 1] for e in improved.effects if e.kind == "cooldown"), 0.0) if rank else 0.0
        cooldown = nova.cooldown + cut  # Improved Frost Nova's value is negative
        if cooldown > 0:
            melee_bonus_dps = frozen_hit_gain(char, filler, target_level=char.level,
                                       assumptions=assumptions) / cooldown
    return Side(
        health=health,
        dps=rotation(char, filler, target_level=char.level,
                     assumptions=assumptions, sustained=False).dps,
        absorb_per_min=s.components["barrier"] * health,
        immunity_share=s.components["immunity"],
        root=c.components["root"],
        stun=c.components["stun"],
        slow=c.components["slow"],
        interrupt=c.components["interrupt"],
        melee_bonus_dps=melee_bonus_dps,
        root_targets=2 if nova is not None else 1,   # Frost Nova roots every nearby enemy (#287)
    )
