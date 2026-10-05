"""World-PvP duel model (#26): an expected time-to-kill race between a mage build and an
opponent kit (docs/design/pvp-duel-model.md).

The score is a ratio of expected times - 0 the mage always loses, 0.5 even, 1 always wins -
not a win probability. Formulas are pinned by tests/test_duel.py and tests/test_duel_dr.py;
constants come from config/duel.toml and opponent kits from config/opponents/*.toml.
"""

from __future__ import annotations

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


@dataclass(frozen=True)
class MageSide:
    """The mage's side of a duel: health, DPS and control in seconds per minute."""

    health: float
    dps: float
    barrier_per_min: float  # Ice Barrier absorb per minute
    immunity_share: float  # share of the fight spent immune (Ice Block + Cold Snap)
    root: float
    stun: float
    slow: float  # uptime x strength, 0-1
    interrupt: float
    nova_dps: float = 0.0  # extra DPS against melee: one frozen hit per Frost Nova (#97)


@dataclass(frozen=True)
class DuelResult:
    """One duel: expected kill times in seconds and the score (0-1, 0.5 even)."""

    score: float
    t_mage: float
    t_opponent: float
    mage_uptime: float
    opponent_uptime: float


def load_kits(directory: Path = OPPONENTS) -> list[Kit]:
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


def _kiting_seconds(mage: MageSide, kit: Kit, c: dict[str, Any]) -> float:
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


def duel(mage: MageSide, kit: Kit, variant: str) -> DuelResult:
    """The expected-kill race between `mage` and `kit`.

    `variant` is "mage_sees" (the mage reacts first) or "they_open" (the opponent gets its
    burst opener and opening stun before the mage acts)."""
    c = _config()
    max_fight = c["max_fight"]

    # Energy budget (#121): a kit with one spends at most max_control_energy_share of its
    # energy on controls; f scales every control's rate before the DR caps.
    spend = sum(ctrl.energy * 60 / ctrl.cooldown
                for ctrl in kit.controls if ctrl.cooldown > 0)
    if kit.energy_per_minute > 0 and spend > 0:
        f = min(1.0, kit.energy_per_minute * c["max_control_energy_share"] / spend)
    else:
        f = 1.0
    categories: dict[str, float] = {}
    uncapped = 0.0
    for ctrl in kit.controls:
        if ctrl.cooldown <= 0 or ctrl.kind not in CAST_LOCKS:
            continue
        rate = ctrl.duration * 60 / ctrl.cooldown * f
        if ctrl.kind in DR_KINDS:
            categories[ctrl.kind] = categories.get(ctrl.kind, 0.0) + rate
        else:  # interrupts and silences have no diminishing returns
            uncapped += rate
    lockout = uncapped
    for kind, total in categories.items():
        longest = max(ctrl.duration for ctrl in kit.controls if ctrl.kind == kind)
        cap = 60 * c["dr_chain"] * longest / (c["dr_chain"] * longest + c["dr_immune_seconds"])
        lockout += min(total, cap)
    mage_uptime = max(c["min_uptime"], 1 - lockout / 60)
    opponent_uptime = max(c["min_uptime"], 1 - _kiting_seconds(mage, kit, c) / 60)

    immune_share = kit.immunity[0] / kit.immunity[1] if kit.immunity else 0.0
    dps = mage.dps + (mage.nova_dps if kit.role == "melee" else 0.0)  # Nova needs them in melee
    t_mage = kit.health / (dps * mage_uptime * (1 - immune_share))

    barrier = mage.barrier_per_min / 60
    if kit.dispels_buffs:
        barrier *= c["dispel_barrier_factor"]
    opponent_dps = kit.dps * opponent_uptime * (1 - mage.immunity_share)

    opening = kit.opener_damage + kit.opener_stun * kit.dps if variant == "they_open" else 0.0
    net = opponent_dps - barrier
    t_opponent = (mage.health - opening) / net if net > 0 else max_fight

    t_mage = min(max(t_mage, 0.0), max_fight)
    t_opponent = min(max(t_opponent, 0.0), max_fight)
    score = 0.5 if t_mage + t_opponent == 0 else t_opponent / (t_mage + t_opponent)
    return DuelResult(score=score, t_mage=t_mage, t_opponent=t_opponent,
                      mage_uptime=mage_uptime, opponent_uptime=opponent_uptime)


def scenario_scores(mage: MageSide, kits: Sequence[Kit]) -> dict[str, dict[str, Any]]:
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


def mage_side(char: Character, filler: SpellRank) -> MageSide:
    """The mage's duel side from a build: short-fight rotation DPS (no sustained buffs)
    plus the survival and control components."""
    s = survival(char, filler)
    c = control(char, filler)
    health = char.stats.health
    assumptions = Assumptions.load()
    nova = best_rank(char.spells, "Frost Nova", char.level)
    nova_dps = 0.0
    if nova is not None:
        improved = next((t for t in char.cls.talents if t.name == "Improved Frost Nova"), None)
        rank = char.ranks.get(improved.talent_id, 0) if improved else 0
        cut = next((e.values[rank - 1] for e in improved.effects if e.kind == "cooldown"), 0.0) if rank else 0.0
        cooldown = nova.cooldown + cut  # Improved Frost Nova's value is negative
        if cooldown > 0:
            nova_dps = frozen_hit_gain(char, filler, target_level=char.level,
                                       assumptions=assumptions) / cooldown
    return MageSide(
        health=health,
        dps=rotation(char, filler, target_level=char.level,
                     assumptions=assumptions, sustained=False).dps,
        barrier_per_min=s.components["barrier"] * health,
        immunity_share=s.components["immunity"],
        root=c.components["root"],
        stun=c.components["stun"],
        slow=c.components["slow"],
        interrupt=c.components["interrupt"],
        nova_dps=nova_dps,
    )
