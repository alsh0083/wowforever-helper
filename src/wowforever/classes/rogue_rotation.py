"""Rogue sustained single-target rotation (#131, part 3): white swings plus an energy cycle of
builders to five combo points and a finisher, with Slice and Dice kept up.

Formulas: docs/tasks/131-rogue-rotation.md, pinned by tests/test_rogue_rotation.py. Numbers come
from the parsed spells (#131 part 1), the rogue's talent effect rules (part 2), the stat table
(#129), the physical combat table (#130) and config/rogue.toml.

Against a pack (`pack` > 1, AoE pulls #262), Blade Flurry's attacks also hit a second mob for its
share of the cooldown (15 s of 120 s), averaged like its haste.

Poisons (#387): classes/poisons.py, on every landed hit. Backstab (#392): the builder when the
caller passes backstab=True with a dagger row.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from wowforever.calc.ev import miss_chance
from wowforever.classes.poisons import best_poisons
from wowforever.melee_stats import MeleeStats
from wowforever.physical import (Attacker, Target, land_chance, white_land_chance, white_swing,
                                 yellow_attack, yellow_crit_chance)
from wowforever.scenarios import best_rank
from wowforever.schema import ClassData, SpellRank
from wowforever.toml_cache import load_toml

CONFIG = Path(__file__).resolve().parents[3] / "config" / "rogue.toml"


@dataclass(frozen=True)
class RogueRotation:
    dps: float
    white_dps: float
    yellow_dps: float
    builder: str              # spell name
    energy_per_second: float
    cycles_per_second: float  # builder-to-finisher cycles
    aoe: tuple[str, ...] = ()  # abilities that hit more than one mob of the pack (#262)
    poisons: tuple[str, ...] = ()   # the poison on each weapon (main hand, then off hand), #387
    poison_dps: float = 0.0
    opener_damage: float = 0.0   # once per kill: Ambush, Initiative, Remorseless Attacks (#431)


def rogue_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                   ranks: Mapping[int, int], target: Target, *, pack: int = 1,
                   backstab: bool = False) -> RogueRotation:
    """Sustained DPS against `target` with the rogue's talents `ranks`; with `pack` > 1, the damage
    summed over a pack of that many such mobs (#262)."""
    c = load_toml(CONFIG)
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
    elif backstab and learned("Backstab") is not None:
        builder, speed = learned("Backstab"), c["normalized_speed"]["dagger"]
    else:
        builder, speed = learned("Sinister Strike"), c["normalized_speed"]["one_hand"]
    hands = [stats.main_hand, stats.off_hand][:max(1, builder.weapon_hits)]
    crit_bonus = total("crit_chance", builder.name)
    def strike(spell: SpellRank, spell_speed: float, weapons, extra_crit: float = 0.0) -> float:
        """Expected damage of `spell` hitting with each of `weapons` (#431: also Ambush, and Remorseless' crit)."""
        out = 0.0
        for weapon in weapons:
            norm = (weapon[0] + weapon[1]) / 2 + stats.attack_power / 14 * spell_speed
            base = (norm + spell.weapon_bonus) * (spell.weapon_pct / 100 if spell.weapon_pct else 1)
            out += yellow_attack(base, attacker, target, crit_bonus=total("crit_chance", spell.name) + extra_crit,
                                 damage_pct=total("damage_pct", spell.name),
                                 crit_damage_pct=total("crit_damage_pct", spell.name), dodge_reduction=dr)
        return out

    builder_ev = strike(builder, speed, hands)
    # once per kill (#431): with a dagger, Ambush from stealth replaces the first builder and Initiative's combo
    # point saves another; Remorseless Attacks crits the first attack after a kill
    after_kill = total("crit_chance", "@after_kill")
    ambush = learned("Ambush") if backstab else None
    opener = 0.0
    if ambush is not None:
        opener = (strike(ambush, c["normalized_speed"]["dagger"], [stats.main_hand], after_kill) - builder_ev
                  + total("proc_chance", "@initiative") / 100 * builder_ev)
    elif after_kill > 0:
        opener = strike(builder, speed, hands, after_kill) - builder_ev
    cost = builder.energy_cost + total("energy_cost", builder.name)
    land = land_chance(attacker, target, dodge_reduction=dr)
    crit = yellow_crit_chance(attacker, target, crit_bonus)
    crit_use = 1 - (1 - crit) ** len(hands)
    cp = builder.combo_points * land + land * crit_use * total("proc_chance", "@builder_crit") / 100
    if builder.name == "Backstab":
        cp += land * total("proc_chance", "@backstab_combo") / 100   # Puncturing Wounds (#392)

    k = c["finisher_combo_points"]
    evis = learned("Eviscerate")
    evis_ev = yellow_attack((evis.min_damage + evis.max_damage) / 2 + evis.per_combo_point * k,
                            attacker, target, damage_pct=total("damage_pct", "Eviscerate"),
                            dodge_reduction=dr)
    refund = total("resource", "@finisher") / 100 * k * 25

    start = total("proc_chance", "@finisher") / 100
    n = (k - start) / cp
    cycles = energy / (n * cost + evis.energy_cost + total("energy_cost", "Eviscerate") - refund)
    finish_share = 1.0
    if snd is not None:
        snd_seconds = ((snd.duration + c["snd_seconds_per_combo_point"] * k)
                       * (1 + total("duration", "Slice and Dice") / 100))
        finish_share = max(0.0, 1 - (1 / snd_seconds) / cycles)
    yellow = cycles * (n * builder_ev + finish_share * evis_ev)
    # poisons (#387): every landed hit of a poisoned weapon can apply its poison
    p = c["poisons"]
    white_land = white_land_chance(attacker, target, dual_wield=dual, dodge_reduction=dr)
    hits = [haste / stats.main_hand[2] * white_land + cycles * land * (n + finish_share)]
    if dual:
        hits.append(haste / stats.off_hand[2] * white_land
                    + (cycles * land * n if builder.weapon_hits >= 2 else 0.0))
    chance = total("proc_chance", "@poison")
    known = tuple(s for s in map(learned, ("Instant Poison", "Deadly Poison")) if s is not None)
    poison_dps, poisons = best_poisons(
        known, tuple(hits),
        chance_pct={"Instant Poison": p["instant_chance_pct"] + chance,
                    "Deadly Poison": p["deadly_chance_pct"] + chance},
        land=1 - miss_chance(level, level + target.level_diff, 0.0) / 100,
        crit=yellow_crit_chance(attacker, target), damage_pct=total("damage_pct", "@poison"),
        max_stacks=p["deadly_max_stacks"])
    yellow += poison_dps
    aoe: tuple[str, ...] = ()
    if pack > 1 and taken("Blade Flurry"):
        bf = c["blade_flurry"]
        share = bf["duration"] / bf["cooldown"]
        white, yellow, aoe = white * (1 + share), yellow * (1 + share), ("Blade Flurry",)
    return RogueRotation(dps=white + yellow, white_dps=white, yellow_dps=yellow, builder=builder.name,
                         energy_per_second=energy, cycles_per_second=cycles, aoe=aoe,
                         poisons=poisons, poison_dps=poison_dps, opener_damage=opener)
