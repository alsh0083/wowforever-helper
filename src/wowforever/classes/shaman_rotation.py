"""Enhancement sustained single-target rotation (#175): two-hander swings with Windfury procs and
Flurry, Stormstrike on cooldown, and Earth Shock on the shock cooldown.

Windfury's chance and bonus attack power are Classic values (config/shaman.toml); Elemental Weapons
raises the bonus. Earth Shock is a spell: it rolls spell hit and crit at base damage (the melee
stat table carries no spell power).

Not modeled yet: Stormstrike's Nature-damage debuff, Maelstrom Weapon's cheaper Lightning Bolt,
Lightning Shield orbs, totems, and mana (shocks are the main cost).
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from wowforever.calc.ev import miss_chance
from wowforever.melee_stats import MeleeStats
from wowforever.physical import Attacker, Target, white_swing, yellow_attack, yellow_crit_chance
from wowforever.scenarios import _anchor_at, best_rank
from wowforever.schema import ClassData, SpellRank

CONFIG = Path(__file__).resolve().parents[3] / "config" / "shaman.toml"


@dataclass(frozen=True)
class EnhancementRotation:
    dps: float
    white_dps: float
    yellow_dps: float
    spell_dps: float


def enhancement_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                         ranks: Mapping[int, int], target: Target) -> EnhancementRotation:
    """Sustained Enhancement DPS against `target` with the shaman's talents `ranks`."""
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

    weapon = stats.main_hand
    if weapon is None:
        return EnhancementRotation(0.0, 0.0, 0.0, 0.0)
    ap = stats.attack_power + total("ap_from_int_pct", "all") / 100 * stats.intellect
    attacker = Attacker(level, ap, stats.crit_pct + total("crit_chance", "all"), stats.hit_pct + total("hit_chance", "all"))
    crit = yellow_crit_chance(attacker, target)

    haste = 1.0
    if taken("Flurry"):
        uptime = 1 - (1 - crit) ** c["flurry_swings"]
        haste *= 1 + total("haste_pct", "@flurry") / 100 * uptime
    if taken("Rage of the Farseer"):
        rf = c["rage_of_the_farseer"]
        haste *= 1 + rf["haste_pct"] / 100 * rf["duration"] / rf["cooldown"]
    swings = haste / weapon[2]
    swing = white_swing(weapon, attacker, target)
    white = swings * swing

    yellow = 0.0
    if level >= 30 and best_rank(spells, "Windfury Weapon", level) is not None:
        bonus = _anchor_at(c["windfury_attack_power"], level)[0] * (1 + total("damage_pct", "Windfury Weapon") / 100)
        extra = white_swing(weapon, replace(attacker, attack_power=ap + bonus), target)
        yellow += swings * c["windfury_chance"] * extra

    storm = best_rank(spells, "Stormstrike", level)
    if storm is not None and taken("Stormstrike") and storm.cooldown > 0:
        normalized = (weapon[0] + weapon[1]) / 2 + ap / 14 * c["normalized_speed"]["two_hand"]
        yellow += yellow_attack(normalized, attacker, target, crit_damage_pct=total("crit_damage_pct", "@ability")) / storm.cooldown

    spell_dps = 0.0
    shock = best_rank(spells, "Earth Shock", level)
    if shock is not None and shock.cooldown > 0:
        hit = 1 - miss_chance(level, level + target.level_diff, stats.hit_pct) / 100
        spell_crit = min(1.0, (stats.crit_pct + total("crit_chance", "all")) / 100)
        avg = (shock.min_damage + shock.max_damage) / 2 * (1 + total("damage_pct", "Earth Shock") / 100)
        spell_dps = hit * avg * (1 + spell_crit * 0.5) / max(shock.cooldown + total("cooldown", "Earth Shock"), 1.5)
    return EnhancementRotation(dps=white + yellow + spell_dps, white_dps=white, yellow_dps=yellow, spell_dps=spell_dps)
