"""Warrior sustained single-target rotation (#162): two-hander white swings build Rage, which goes
to Mortal Strike and Whirlwind on cooldown, then to Heroic Strike on the next swings.

Rage comes from damage dealt (Classic conversion, config/warrior.toml), Unbridled Wrath, Anger
Management and Bloodrage. A Heroic Strike replaces a white swing, so it also gives up that swing's
Rage. Numbers come from the parsed spells, the warrior's talent effect rules, the stat table and
the physical combat table.

Not modeled yet: Fury dual wield and Bloodthirst, Flurry, Execute below 20%, Overpower procs, Slam,
Sweeping Strikes' second target, and Rage from damage taken.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from wowforever.melee_stats import MeleeStats
from wowforever.physical import Attacker, Target, land_chance, white_swing, yellow_attack, yellow_crit_chance
from wowforever.scenarios import best_rank
from wowforever.schema import ClassData, SpellRank

CONFIG = Path(__file__).resolve().parents[3] / "config" / "warrior.toml"


@dataclass(frozen=True)
class WarriorRotation:
    dps: float
    white_dps: float
    yellow_dps: float
    rage_per_second: float
    abilities: tuple[str, ...]     # spells the rotation uses, in priority order


def rage_conversion(level: int) -> float:
    """Classic damage-to-Rage divisor at `level`."""
    k = tomllib.loads(CONFIG.read_text(encoding="utf-8"))["rage_conversion"]
    return k["a"] * level ** 2 + k["b"] * level + k["k"]


def warrior_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                     ranks: Mapping[int, int], target: Target) -> WarriorRotation:
    """Sustained DPS against `target` with the warrior's talents `ranks`."""
    c = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
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

    weapon = stats.main_hand
    if weapon is None:
        return WarriorRotation(0.0, 0.0, 0.0, 0.0, ())
    attacker = Attacker(level, stats.attack_power, stats.crit_pct + total("crit_chance", "all"),
                        stats.hit_pct + total("hit_chance", "all"))
    weapon_pct = total("damage_pct", "@two_hand")
    death_wish = 1.0
    if taken("Death Wish"):
        dw = c["death_wish"]
        death_wish += dw["bonus_pct"] / 100 * dw["duration"] / dw["cooldown"]
    conv = 7.5 / rage_conversion(level)

    swings = 1 / weapon[2]
    swing_ev = white_swing(weapon, attacker, target, damage_pct=weapon_pct)
    rage_per_swing = swing_ev * conv + land_chance(attacker, target) * total("proc_chance", "@white_rage") / 100
    income = swings * rage_per_swing
    bloodrage = learned("Bloodrage")
    if bloodrage is not None and bloodrage.cooldown > 0:
        income += c["bloodrage_rage"] / bloodrage.cooldown
    if taken("Anger Management"):
        income += c["anger_management_rage_per_second"]

    avg_weapon = (weapon[0] + weapon[1]) / 2
    normalized = avg_weapon + stats.attack_power / 14 * c["normalized_speed"]["two_hand"]
    crit_damage = total("crit_damage_pct", "@ability")

    def strike(spell: SpellRank) -> float:
        base = (normalized if spell.weapon_normalized else avg_weapon + stats.attack_power / 14 * weapon[2])
        return yellow_attack(base + spell.weapon_bonus, attacker, target,
                             crit_bonus=total("crit_chance", spell.name),
                             damage_pct=weapon_pct + total("damage_pct", spell.name),
                             crit_damage_pct=crit_damage)

    def cost(spell: SpellRank) -> float:
        return max(0.0, spell.rage_cost + total("rage_cost", spell.name))

    rage, yellow, used, crits = income, 0.0, [], 0.0
    for name in ("Mortal Strike", "Whirlwind"):
        spell = learned(name)
        if spell is None or spell.cooldown <= 0 or (name == "Mortal Strike" and not taken(name)):
            continue
        rate = min(1 / spell.cooldown, rage / cost(spell)) if cost(spell) else 1 / spell.cooldown
        rage -= rate * cost(spell)
        yellow += rate * strike(spell)
        crits += rate * land_chance(attacker, target) * yellow_crit_chance(attacker, target,
                                                                           total("crit_chance", name))
        used.append(name)

    heroic = learned("Heroic Strike")
    hs_rate = 0.0
    if heroic is not None and rage > 0:
        # each Heroic Strike costs its Rage plus the Rage its white swing would have made
        hs_rate = min(swings, rage / (cost(heroic) + rage_per_swing))
        yellow += hs_rate * (strike(heroic) - swing_ev)
        crits += hs_rate * land_chance(attacker, target) * yellow_crit_chance(attacker, target)
        used.append("Heroic Strike")
    white = swings * swing_ev

    # Deep Wounds: every crit bleeds a share of the weapon's average damage
    crits += (swings - hs_rate) * land_chance(attacker, target) * yellow_crit_chance(attacker, target)
    bleed = crits * total("dot_pct", "@crit") / 100 * avg_weapon
    yellow += bleed

    return WarriorRotation(dps=(white + yellow) * death_wish, white_dps=white * death_wish,
                           yellow_dps=yellow * death_wish, rage_per_second=income, abilities=tuple(used))
