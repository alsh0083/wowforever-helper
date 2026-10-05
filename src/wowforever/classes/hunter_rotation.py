"""Hunter sustained single-target rotation (#132, part 2): ranged (Auto Shot plus Aimed, Multi and
Arcane Shot on cooldown, Serpent Sting kept up) or petless dual-wield melee for Forever's Lone Wolf
Survival (white swings, Raptor Strike, Mongoose Bite with Lacerating Strikes, Strider Kick), plus an
estimated pet for Beast Mastery. The rotation reports the better of ranged and melee.

Pinned by tests/test_hunter_rotation.py; constants in config/hunter.toml.

Not modeled yet: Rapid Killing's cooldown cut, Deadly Aspects procs, Expose Prey, hawk damage,
Resourcefulness, and pet talents beyond Unleashed Fury and Bestial Wrath.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from wowforever.melee_stats import MeleeStats
from wowforever.physical import Attacker, Target, land_chance, ranged_shot, white_swing, yellow_attack
from wowforever.scenarios import best_rank
from wowforever.schema import ClassData, SpellRank

CONFIG = Path(__file__).resolve().parents[3] / "config" / "hunter.toml"
MELEE = Path(__file__).resolve().parents[3] / "config" / "melee.toml"


@dataclass(frozen=True)
class HunterRotation:
    dps: float
    ranged_dps: float
    melee_dps: float
    pet_dps: float
    mode: str                 # "ranged" or "melee", whichever is higher
    mana_per_second: float    # of the chosen mode
    auto_dps: float = 0.0     # Auto Shot alone (costs no mana), the fallback once out of mana


def hunter_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                    ranks: Mapping[int, int], target: Target, *, pet: bool = False) -> HunterRotation:
    """Sustained DPS against `target`; `pet` adds a pet and turns Lone Wolf off."""
    c = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    agi_per_crit = tomllib.loads(MELEE.read_text(encoding="utf-8"))["hunter"]["agi_per_crit_at_60"]
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

    def learned(name: str) -> SpellRank | None:
        return best_rank(spells, name, level)

    # stats every attack shares
    extra_agi = stats.agility * total("stat_pct", "agility") / 100
    int_ap = stats.intellect * total("ap_from_int_pct", "all") / 100
    agi_crit = extra_agi / (agi_per_crit * level / 60)
    hit = stats.hit_pct + total("hit_chance", "all")
    crit_all = total("crit_chance", "all") + agi_crit
    shared_pct = (0.0 if pet else total("damage_pct", "@no_pet")) + (total("damage_pct", "@with_pet") if pet else 0.0)
    efficiency = 1 + total("mana_cost_pct", "@shot") / 100

    # ranged
    ranged = mana_r = auto = 0.0
    if stats.ranged is not None:
        rap = stats.ranged_attack_power + int_ap + 2 * extra_agi + (c["trueshot_aura_rap"] if taken("Trueshot Aura") else 0)
        a_r = Attacker(level, rap, stats.ranged_crit_pct + crit_all, hit)
        weapon_pct = total("damage_pct", "@ranged") + shared_pct
        cd_r = total("crit_damage_pct", "@ranged")
        low, high, speed = stats.ranged
        haste = 1 + c["quiver_haste_pct"] / 100
        rapid = learned("Rapid Fire")
        if rapid is not None:
            haste *= 1 + rapid.haste_pct / 100 * rapid.duration / rapid.cooldown
        auto = ranged_shot((low + high) / 2 + rap / 14 * speed, a_r, target, damage_pct=weapon_pct,
                           crit_damage_pct=cd_r) * haste / speed
        norm = (low + high) / 2 + rap / 14 * c["normalized_speed"]["ranged"]
        shots, casting = 0.0, 0.0
        for name, flat in (("Aimed Shot", False), ("Multi-Shot", False), ("Arcane Shot", True)):
            shot = learned(name)
            if shot is None:
                continue
            cooldown = shot.cooldown + total("cooldown", name)
            if flat:
                ev = ranged_shot((shot.min_damage + shot.max_damage) / 2, a_r, target,
                                 damage_pct=shared_pct, crit_damage_pct=cd_r)
            else:
                ev = ranged_shot(norm + shot.weapon_bonus, a_r, target,
                                 damage_pct=weapon_pct + total("damage_pct", name), crit_damage_pct=cd_r)
            shots += ev / cooldown
            casting += shot.cast_time / cooldown
            mana_r += shot.mana_cost * efficiency / cooldown
        sting = learned("Serpent Sting")
        dot = 0.0
        if sting is not None:
            dot = (sting.periodic_damage * (1 + (total("damage_pct", "Serpent Sting") + shared_pct) / 100)
                   * land_chance(a_r, target, can_dodge=False) / sting.duration)
            mana_r += sting.mana_cost * (1 + total("mana_cost_pct", "@sting") / 100) / sting.duration
        ranged = auto * (1 - casting) + shots + dot

    # petless dual-wield melee
    melee = mana_m = 0.0
    if stats.main_hand is not None:
        ap = stats.attack_power + int_ap + extra_agi
        a_m = Attacker(level, ap, stats.crit_pct + crit_all + total("crit_chance", "@melee"), hit)
        cd_m = total("crit_damage_pct", "@melee")
        dual = stats.off_hand is not None
        mh_swing = white_swing(stats.main_hand, a_m, target, dual_wield=dual, damage_pct=shared_pct,
                               crit_damage_pct=cd_m)
        melee = mh_swing / stats.main_hand[2]
        if dual:
            melee += white_swing(stats.off_hand, a_m, target, dual_wield=True, off_hand=True,
                                 damage_pct=shared_pct + total("damage_pct", "@off_hand"),
                                 crit_damage_pct=cd_m) / stats.off_hand[2]
        mh_avg = (stats.main_hand[0] + stats.main_hand[1]) / 2
        melee_cost = 1 + total("mana_cost_pct", "@melee") / 100
        raptor = learned("Raptor Strike")
        if raptor is not None:  # replaces a main-hand swing
            every = max(raptor.cooldown, stats.main_hand[2])
            hit_ev = yellow_attack(mh_avg + ap / 14 * stats.main_hand[2] + raptor.weapon_bonus, a_m, target,
                                   damage_pct=shared_pct, crit_damage_pct=cd_m)
            melee += (hit_ev - mh_swing) / every
            mana_m += raptor.mana_cost * melee_cost / every
        for name in ("Mongoose Bite", "Strider Kick"):
            strike = learned(name)
            if strike is None:
                continue
            base = mh_avg + ap / 14 * c["normalized_speed"]["one_hand"] + strike.weapon_bonus
            base *= strike.weapon_pct / 100 if strike.weapon_pct else 1
            ev = yellow_attack(base, a_m, target, damage_pct=shared_pct, crit_damage_pct=cd_m)
            ev *= 1 + total("dot_pct", name) / 100          # Lacerating Strikes' bleed
            melee += ev / strike.cooldown
            mana_m += strike.mana_cost * melee_cost / strike.cooldown

    pet_dps = 0.0
    if pet:
        pet_dps = c["pet_dps_per_level"] * level * (1 + total("damage_pct", "@pet") / 100)
        if taken("Bestial Wrath"):
            bw = c["bestial_wrath"]
            pet_dps *= 1 + bw["bonus_pct"] / 100 * bw["duration"] / bw["cooldown"]
        pet_dps *= 1 + total("damage_pct", "@with_pet") / 100

    mode = "ranged" if ranged >= melee else "melee"
    best = max(ranged, melee)
    return HunterRotation(dps=best + pet_dps, ranged_dps=ranged, melee_dps=melee, pet_dps=pet_dps, mode=mode,
                          mana_per_second=mana_r if mode == "ranged" else mana_m, auto_dps=auto)
