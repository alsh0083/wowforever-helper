"""Retribution sustained single-target rotation (#175): two-hander white swings with Seal of Command
procs, Judgement on cooldown and Holy Strike on cooldown.

Seal of Command and Judgement are Holy damage, so armor doesn't reduce them; they still roll the
melee table's miss and crit. Constants that the client data doesn't carry (proc rate, Judgement of
Command's damage) are Classic values in config/paladin.toml.

Not modeled yet: Consecration, Exorcism and Hammer of Wrath (target or health limits), Vindication's
attack power, Twist of Light's echo, Champion of the Light's spell power, and mana (Retribution's
seal and strike costs are small next to its pool).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from wowforever.melee_stats import MeleeStats
from wowforever.physical import Attacker, Target, white_swing, yellow_attack
from wowforever.scenarios import best_rank
from wowforever.schema import ClassData, SpellRank
from wowforever.toml_cache import load_toml

CONFIG = Path(__file__).resolve().parents[3] / "config" / "paladin.toml"


@dataclass(frozen=True)
class PaladinRotation:
    dps: float
    white_dps: float
    holy_dps: float
    abilities: tuple[str, ...]


def paladin_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                     ranks: Mapping[int, int], target: Target) -> PaladinRotation:
    """Sustained DPS against `target` with the paladin's talents `ranks`."""
    c = load_toml(CONFIG)
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

    weapon = stats.main_hand
    if weapon is None:
        return PaladinRotation(0.0, 0.0, 0.0, ())
    attacker = Attacker(stats.level, stats.attack_power, stats.crit_pct + total("crit_chance", "all"),
                        stats.hit_pct + total("hit_chance", "all"))
    holy_target = replace(target, armor=0.0)          # Holy damage ignores armor
    all_pct = total("damage_pct", "all")
    weapon_pct = total("damage_pct", "@two_hand") + all_pct
    avg = (weapon[0] + weapon[1]) / 2 + stats.attack_power / 14 * weapon[2]
    swings = 1 / weapon[2]
    white = swings * white_swing(weapon, attacker, target, damage_pct=weapon_pct)
    holy, used = 0.0, []

    if taken("Seal of Command") and best_rank(spells, "Seal of Command", stats.level) is not None:
        chance = c["seal_of_command_ppm"] * weapon[2] / 60
        proc = yellow_attack(avg * c["seal_of_command_weapon_pct"] / 100, attacker, holy_target,
                             damage_pct=all_pct + total("damage_pct", "Seal of Command"))
        holy += swings * chance * proc
        judgement = best_rank(spells, "Judgement", stats.level)
        if judgement is not None:
            from wowforever.scenarios import _anchor_at

            damage = _anchor_at(c["judgement_of_command"], stats.level)[0]
            cooldown = max(1.0, judgement.cooldown + total("cooldown", "Judgement"))
            holy += yellow_attack(damage, attacker, holy_target,
                                  damage_pct=all_pct + total("damage_pct", "Judgement")) / cooldown
            used += ["Seal of Command", "Judgement"]

    strike = best_rank(spells, "Holy Strike", stats.level)
    if strike is not None and strike.cooldown > 0:
        normalized = (weapon[0] + weapon[1]) / 2 + stats.attack_power / 14 * c["normalized_speed"]["two_hand"]
        base = (normalized + strike.weapon_bonus) * (strike.weapon_pct / 100 if strike.weapon_pct else 1)
        holy += yellow_attack(base, attacker, holy_target, crit_bonus=total("crit_chance", "Holy Strike"),
                              damage_pct=all_pct + total("damage_pct", "Holy Strike")) / strike.cooldown
        used.append("Holy Strike")
    return PaladinRotation(dps=white + holy, white_dps=white, holy_dps=holy, abilities=tuple(used))
