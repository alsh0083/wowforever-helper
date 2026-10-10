"""Feral cat sustained single-target rotation (#175): paw swings plus an energy cycle of builders
to five combo points and Ferocious Bite, the rogue model (#131) in cat form.

Cat form replaces the weapon with paws (Classic damage by level, config/druid.toml) and Predatory
Strikes adds attack power by level. The builder is Shred when Shredding Attacks makes it cheap,
otherwise Claw; Rend and Tear counts as always on (Rake keeps the target bleeding).

Not modeled yet: Rake's and Rip's bleeds as separate damage, Tiger's Fury, Berserk's cleave,
Omen of Clarity, powershifting and Shifting Power.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from wowforever.melee_stats import MeleeStats
from wowforever.physical import Attacker, Target, land_chance, white_swing, yellow_attack
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
    builder_ev = yellow_attack(base, attacker, target, damage_pct=bleeding + total("damage_pct", builder.name),
                               crit_damage_pct=crit_damage)
    cost = max(0.0, builder.energy_cost + total("energy_cost", builder.name))
    cp_per_builder = builder.combo_points * land_chance(attacker, target)

    k = c["finisher_combo_points"]
    bite = best_rank(spells, "Ferocious Bite", level)
    yellow = 0.0
    energy = c["energy_per_second"]
    if bite is not None and cp_per_builder > 0:
        bite_ev = yellow_attack((bite.min_damage + bite.max_damage) / 2 + bite.per_combo_point * k, attacker, target,
                                damage_pct=bleeding + total("damage_pct", "Ferocious Bite"), crit_damage_pct=crit_damage)
        n = k / cp_per_builder
        cycles = energy / (n * cost + bite.energy_cost)
        yellow = cycles * (n * builder_ev + bite_ev)
    elif cost > 0:
        yellow = energy / cost * builder_ev
    return CatRotation(dps=white + yellow, white_dps=white, yellow_dps=yellow, builder=builder.name)
