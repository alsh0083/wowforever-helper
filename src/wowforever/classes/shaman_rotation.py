"""Enhancement sustained single-target rotation (#175): two-hander swings with Windfury procs and
Flurry, Stormstrike on cooldown, and Earth Shock on the shock cooldown.

Windfury's chance and bonus attack power are Classic values (config/shaman.toml); Elemental Weapons
raises the bonus. Earth Shock is a spell: it rolls spell hit and crit at base damage (the melee
stat table carries no spell power).

Against a pack (`pack` > 1, AoE pulls #262) Fire Nova goes out on cooldown and hits every mob, rolled
like Earth Shock.

Stormstrike's bonus on the next Earth Shock counts for the share of shocks after one (#398).
Not modeled yet: Maelstrom Weapon's cheaper Lightning Bolt,
Lightning Shield orbs, totems, and mana (shocks are the main cost).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from wowforever.calc.ev import miss_chance
from wowforever.melee_stats import MeleeStats
from wowforever.physical import Attacker, Target, white_swing, yellow_attack, yellow_crit_chance
from wowforever.scenarios import _anchor_at, best_rank
from wowforever.schema import ClassData, SpellRank
from wowforever.toml_cache import load_toml

CONFIG = Path(__file__).resolve().parents[3] / "config" / "shaman.toml"


@dataclass(frozen=True)
class EnhancementRotation:
    dps: float
    white_dps: float
    yellow_dps: float
    spell_dps: float
    aoe: tuple[str, ...] = ()   # spells that hit more than one mob of the pack (#262)


def enhancement_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                         ranks: Mapping[int, int], target: Target, *, pack: int = 1) -> EnhancementRotation:
    """Sustained Enhancement DPS against `target` with the shaman's talents `ranks`; with `pack` > 1, the
    damage summed over a pack of that many such mobs (#262)."""
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

    weapon = stats.main_hand
    if weapon is None:
        return EnhancementRotation(0.0, 0.0, 0.0, 0.0)
    ap = stats.attack_power + total("ap_from_int_pct", "all") / 100 * stats.intellect
    melee_crit = stats.crit_pct + total("crit_chance", "all")
    shock = best_rank(spells, "Earth Shock", level)
    if shock is not None and shock.cooldown > 0 and total("duration", "@devastation") > 0:
        # Earth Shock crits raise melee crit for a while (Elemental Devastation, #398): its average uptime
        shocks = total("duration", "@devastation") / max(shock.cooldown + total("cooldown", "Earth Shock"), 1.5)
        uptime = 1 - (1 - min(1.0, (stats.crit_pct + total("crit_chance", "all")) / 100)) ** shocks
        melee_crit += total("crit_chance", "@devastation") * uptime
    attacker = Attacker(level, ap, melee_crit, stats.hit_pct + total("hit_chance", "all"))
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
    hit = 1 - miss_chance(level, level + target.level_diff, stats.hit_pct) / 100
    spell_crit = min(1.0, (stats.crit_pct + total("crit_chance", "all")) / 100)
    spell_power = stats.intellect * total("spell_power_from", "intellect") / 100   # Mental Quickness (#398)
    shock = best_rank(spells, "Earth Shock", level)
    if shock is not None and shock.cooldown > 0:
        avg = (((shock.min_damage + shock.max_damage) / 2 + shock.coefficient * spell_power)
               * (1 + total("damage_pct", "Earth Shock") / 100))
        shock_period = max(shock.cooldown + total("cooldown", "Earth Shock"), 1.5)
        spell_dps = hit * avg * (1 + spell_crit * 0.5) / shock_period
        if storm is not None and taken("Stormstrike") and storm.cooldown > 0:
            # Stormstrike's bonus on the next shock within its window: the share of shocks after one (#398)
            share = min(1.0, shock_period / storm.cooldown) if shock_period <= c["stormstrike"]["seconds"] else 0.0
            spell_dps *= 1 + c["stormstrike"]["bonus_pct"] / 100 * share
    nova = best_rank(spells, "Fire Nova", level) if pack > 1 else None
    aoe: tuple[str, ...] = ()
    if nova is not None and nova.min_damage > 0:
        avg = (((nova.min_damage + nova.max_damage) / 2 + nova.coefficient * spell_power)
               * (1 + total("damage_pct", "Fire Nova") / 100))
        spell_dps += hit * avg * (1 + spell_crit * 0.5) * pack / max(nova.cooldown + total("cooldown", "Fire Nova"), 1.5)
        aoe = ("Fire Nova",)
    return EnhancementRotation(dps=white + yellow + spell_dps, white_dps=white, yellow_dps=yellow, spell_dps=spell_dps,
                               aoe=aoe)
