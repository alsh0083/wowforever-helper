"""Rogue sustained single-target rotation (#131, part 3): white swings plus an energy cycle of
builders to five combo points and a finisher, with Slice and Dice kept up.

Formulas: docs/tasks/131-rogue-rotation.md, pinned by tests/test_rogue_rotation.py. Numbers come
from the parsed spells (#131 part 1), the rogue's talent effect rules (part 2), the stat table
(#129), the physical combat table (#130) and config/rogue.toml.

Not modeled yet: poisons, Backstab (needs the main-hand weapon type), Hack and Slash extra
attacks, and Blade Flurry's second target.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from wowforever.melee_stats import MeleeStats
from wowforever.physical import (Attacker, Target, land_chance, white_swing, yellow_attack,
                                 yellow_crit_chance)
from wowforever.scenarios import best_rank
from wowforever.schema import ClassData, SpellRank

CONFIG = Path(__file__).resolve().parents[3] / "config" / "rogue.toml"


@dataclass(frozen=True)
class RogueRotation:
    dps: float
    white_dps: float
    yellow_dps: float
    builder: str              # spell name
    energy_per_second: float
    cycles_per_second: float  # builder-to-finisher cycles


def rogue_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                   ranks: Mapping[int, int], target: Target) -> RogueRotation:
    """Sustained DPS against `target` with the rogue's talents `ranks`."""
    c = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    level = stats.level
    by_name = {t.name: t for t in cls.talents}

    def taken(name: str) -> bool:
        t = by_name.get(name)
        return t is not None and ranks.get(t.talent_id, 0) > 0

    def total(kind: str, applies: str) -> float:
        """Sum over taken talents of the per-rank value of `kind` effects that apply to `applies`."""
        out = 0.0
        for t in cls.talents:
            rank = ranks.get(t.talent_id, 0)
            if rank <= 0:
                continue
            out += sum(e.values[rank - 1] for e in t.effects if e.kind == kind and applies in e.applies_to)
        return out

    def learned(name: str) -> SpellRank | None:
        return best_rank(spells, name, level)

    attacker = Attacker(level, stats.attack_power, stats.crit_pct + total("crit_chance", "all"),
                        stats.hit_pct + total("hit_chance", "all"))
    dr = total("dodge_reduction", "all")
    target = replace(target, armor=target.armor * (1 - total("armor_pen", "all") / 100))

    snd = learned("Slice and Dice")
    haste = 1 + snd.haste_pct / 100 if snd is not None else 1.0
    if taken("Blade Flurry"):
        bf = c["blade_flurry"]
        haste *= 1 + bf["haste_pct"] / 100 * bf["duration"] / bf["cooldown"]

    dual = stats.main_hand is not None and stats.off_hand is not None
    white = 0.0
    if stats.main_hand is not None:
        white += white_swing(stats.main_hand, attacker, target, dual_wield=dual,
                             dodge_reduction=dr) * haste / stats.main_hand[2]
    if dual:
        white += white_swing(stats.off_hand, attacker, target, dual_wield=True, off_hand=True,
                             damage_pct=total("damage_pct", "@off_hand"),
                             dodge_reduction=dr) * haste / stats.off_hand[2]

    energy = c["energy_per_second"]
    if taken("Adrenaline Rush"):
        ar = c["adrenaline_rush"]
        energy *= 1 + ar["bonus_pct"] / 100 * ar["duration"] / ar["cooldown"]

    if taken("Mutilate") and learned("Mutilate") is not None:
        builder, speed = learned("Mutilate"), c["normalized_speed"]["dagger"]
    elif taken("Hemorrhage") and learned("Hemorrhage") is not None:
        builder, speed = learned("Hemorrhage"), c["normalized_speed"]["one_hand"]
    else:
        builder, speed = learned("Sinister Strike"), c["normalized_speed"]["one_hand"]
    hands = [stats.main_hand, stats.off_hand][:max(1, builder.weapon_hits)]
    crit_bonus = total("crit_chance", builder.name)
    builder_ev = 0.0
    for weapon in hands:
        norm = (weapon[0] + weapon[1]) / 2 + stats.attack_power / 14 * speed
        base = (norm + builder.weapon_bonus) * (builder.weapon_pct / 100 if builder.weapon_pct else 1)
        builder_ev += yellow_attack(base, attacker, target, crit_bonus=crit_bonus,
                                    damage_pct=total("damage_pct", builder.name),
                                    crit_damage_pct=total("crit_damage_pct", builder.name),
                                    dodge_reduction=dr)
    cost = builder.energy_cost + total("energy_cost", builder.name)
    land = land_chance(attacker, target, dodge_reduction=dr)
    crit = yellow_crit_chance(attacker, target, crit_bonus)
    crit_use = 1 - (1 - crit) ** len(hands)
    cp = builder.combo_points * land + land * crit_use * total("proc_chance", "@builder_crit") / 100

    k = c["finisher_combo_points"]
    evis = learned("Eviscerate")
    evis_ev = yellow_attack((evis.min_damage + evis.max_damage) / 2 + evis.per_combo_point * k,
                            attacker, target, damage_pct=total("damage_pct", "Eviscerate"),
                            dodge_reduction=dr)
    refund = total("resource", "@finisher") / 100 * k * 25

    start = total("proc_chance", "@finisher") / 100
    n = (k - start) / cp
    cycles = energy / (n * cost + evis.energy_cost - refund)
    finish_share = 1.0
    if snd is not None:
        snd_seconds = ((snd.duration + c["snd_seconds_per_combo_point"] * k)
                       * (1 + total("duration", "Slice and Dice") / 100))
        finish_share = max(0.0, 1 - (1 / snd_seconds) / cycles)
    yellow = cycles * (n * builder_ev + finish_share * evis_ev)
    return RogueRotation(dps=white + yellow, white_dps=white, yellow_dps=yellow, builder=builder.name,
                         energy_per_second=energy, cycles_per_second=cycles)
