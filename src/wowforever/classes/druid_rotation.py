"""Feral cat sustained single-target rotation (#175): paw swings plus an energy cycle of builders
to five combo points and Ferocious Bite, the rogue model (#131) in cat form.

Cat form replaces the weapon with paws (Classic damage by level, config/druid.toml) and Predatory
Strikes adds attack power by level. The builder is Shred when Shredding Attacks makes it cheap,
otherwise Claw; Rend and Tear counts as always on (Rake keeps the target bleeding).

Rip is kept up when it beats Ferocious Bite (#397). Rake takes a builder's place once per its
duration when it gains (#397). Blood Frenzy's extra combo point on builder crits and Berserk's builder crit
(averaged over a guessed cooldown) count (#397). Not modeled yet: Tiger's Fury, Berserk's cleave, Omen of
Clarity, powershifting and Shifting Power.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from wowforever.melee_stats import MeleeStats
from wowforever.physical import Attacker, Target, land_chance, white_swing, yellow_attack, yellow_crit_chance
from wowforever.scenarios import _anchor_at, best_rank
from wowforever.schema import ClassData, SpellRank
from wowforever.toml_cache import load_toml

CONFIG = Path(__file__).resolve().parents[3] / "config" / "druid.toml"


@dataclass(frozen=True)
class CatRotation:
    dps: float
    white_dps: float
    yellow_dps: float
    builder: str
    builder_ev: float = 0.0                 # one builder's expected damage (#397)
    combo_points_per_builder: float = 0.0


def finisher_dps(energy: float, builders: float, builder_cost: float, builder_ev: float, bite_cost: float,
                 bite_ev: float, rip: tuple[float, float, float] | None = None) -> float:
    """Yellow damage per second of `builders` builders to full combo points and a finisher (#397): Ferocious Bite
    every cycle, or with `rip` = (energy cost, damage, duration) Rip as often as energy allows (at most once per
    duration) and Bite cycles on the energy left."""
    left, out = energy, 0.0
    if rip is not None:
        rip_cost, rip_damage, rip_duration = rip
        cycle = builders * builder_cost + rip_cost
        rate = min(1 / rip_duration, energy / cycle)          # Rip cycles per second
        left -= rate * cycle
        out += rate * (rip_damage + builders * builder_ev)
    return out + left / (builders * builder_cost + bite_cost) * (builders * builder_ev + bite_ev)


def rake_gain(rake_damage: float, builder_ev: float, builder_cost: float, rake_cost: float,
              damage_per_energy: float, duration: float) -> float:
    """Extra damage per second from Rake taking a builder's place once per its duration (#397), or 0 if it loses."""
    gain = (rake_damage - builder_ev + (builder_cost - rake_cost) * damage_per_energy) / duration
    return max(0.0, gain)


def cat_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                 ranks: Mapping[int, int], target: Target) -> CatRotation:
    """Sustained cat DPS against `target` with the druid's talents `ranks`."""
    c = load_toml(CONFIG)
    level = stats.level
    by_name = {t.name: t for t in cls.talents}

    def taken(name: str) -> bool:
        t = by_name.get(name)
        return t is not None and ranks.get(t.talent_id, 0) > 0

    def total(kind: str, applies: str) -> float:
        out = 0.0
        for t in cls.talents:
            rank = ranks.get(t.talent_id, 0)
            if rank > 0:
                out += sum(e.values[rank - 1] for e in t.effects if e.kind == kind and applies in e.applies_to)
        return out

    lo, hi = _anchor_at(c["paws"], level)
    paws = (lo, hi, c["paw_speed"])
    ap = stats.attack_power + total("ap_per_level_pct", "all") / 100 * level
    attacker = Attacker(level, ap, stats.crit_pct + total("crit_chance", "all") + total("crit_chance", "@feral"),
                        stats.hit_pct + total("hit_chance", "all"))
    bleeding = total("damage_pct", "@bleeding")
    white = white_swing(paws, attacker, target, damage_pct=bleeding) / paws[2]

    builder = best_rank(spells, "Shred", level) if taken("Shredding Attacks") else None
    builder = builder or best_rank(spells, "Claw", level)
    if builder is None:
        return CatRotation(white, white, 0.0, "")
    avg = (lo + hi) / 2 + ap / 14 * paws[2]
    crit_damage = total("crit_damage_pct", "@ability")
    base = (avg * (builder.weapon_pct / 100 if builder.weapon_pct else 1)) + builder.weapon_bonus
    share = 0.0
    if taken("Berserk"):
        # Berserk (#397): +100% builder crit for its duration, averaged over its (guessed) cooldown
        share = c["berserk"]["duration"] / c["berserk"]["cooldown"]
    land = land_chance(attacker, target)
    extra_cp = total("proc_chance", "@builder_crit") / 100       # Blood Frenzy (#397)
    builder_ev = cp_per_builder = 0.0
    for weight, bonus in ((1 - share, 0.0), (share, 100.0)):
        if weight <= 0:
            continue
        builder_ev += weight * yellow_attack(base, attacker, target, crit_bonus=bonus,
                                             damage_pct=bleeding + total("damage_pct", builder.name),
                                             crit_damage_pct=crit_damage)
        cp_per_builder += weight * land * (builder.combo_points
                                           + yellow_crit_chance(attacker, target, bonus) * extra_cp)
    cost = max(0.0, builder.energy_cost + total("energy_cost", builder.name))

    k = c["finisher_combo_points"]
    bite = best_rank(spells, "Ferocious Bite", level)
    yellow = 0.0
    energy = c["energy_per_second"]
    if bite is not None and cp_per_builder > 0:
        bite_ev = yellow_attack((bite.min_damage + bite.max_damage) / 2 + bite.per_combo_point * k, attacker, target,
                                damage_pct=bleeding + total("damage_pct", "Ferocious Bite"), crit_damage_pct=crit_damage)
        n = k / cp_per_builder
        yellow = finisher_dps(energy, n, cost, builder_ev, bite.energy_cost, bite_ev)
        rip = best_rank(spells, "Rip", level)
        if rip is not None and rip.duration > 0:
            # Rip at k combo points: a bleed, so it lands or not but armor and crits don't touch it (#397)
            rip_damage = ((rip.periodic_damage + rip.periodic_per_combo_point * k) * land_chance(attacker, target)
                          * (1 + (bleeding + total("damage_pct", "Rip")) / 100))
            yellow = max(yellow, finisher_dps(energy, n, cost, builder_ev, bite.energy_cost, bite_ev,
                                              rip=(rip.energy_cost, rip_damage, rip.duration)))
    elif cost > 0:
        yellow = energy / cost * builder_ev
    rake = best_rank(spells, "Rake", level)
    if rake is not None and rake.duration > 0 and yellow > 0 and energy > 0:
        # Rake in a builder's place once per its duration (#397): its hit and its bleed (armor-free)
        pct = bleeding + total("damage_pct", "Rake")
        rake_damage = (yellow_attack((rake.min_damage + rake.max_damage) / 2, attacker, target, damage_pct=pct,
                                     crit_damage_pct=crit_damage)
                       + rake.periodic_damage * land_chance(attacker, target) * (1 + pct / 100))
        rake_cost = max(0.0, rake.energy_cost + total("energy_cost", "Rake"))
        yellow += rake_gain(rake_damage, builder_ev, cost, rake_cost, yellow / energy, rake.duration)
    return CatRotation(dps=white + yellow, white_dps=white, yellow_dps=yellow, builder=builder.name,
                       builder_ev=builder_ev, combo_points_per_builder=cp_per_builder)
