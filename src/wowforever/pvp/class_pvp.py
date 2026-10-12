"""Rogue, hunter and warrior PvP scores (#134, #162): the mage's duel model (#26, #121) from their side.

The class's side has the same fields as the mage's: health, rotation DPS against player armor, and
what its controls do to the opponent (stuns keep a melee opponent from hitting, interrupts lock a
caster, slows help kiting). Its own controls get the same energy budget and diminishing returns as
opponent kits (config/pvp_self.toml). The score is the mean over the four world-PvP scenarios.

Opponent kits' DPS assumes cloth; physical kits hit these classes by their armor ratio.
Thorns returns damage to melee opponents (#265).
Druids heal themselves with direct heals when that helps (#265).
Not modeled yet: openers from stealth, Evasion, Vanish, Deterrence and Feign Death.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from wowforever.assumptions import Assumptions
from wowforever.calc.ev import GCD_SECONDS
from wowforever.focus import PVP_SCENARIOS
from wowforever.melee_scenarios import build_stats, rotation_output
from wowforever.melee_stats import MeleeStats
from wowforever.physical import Target, armor_factor
from wowforever.pvp.duel import Control, Kit, MageSide, lockout_seconds, scenario_scores
from wowforever.scenarios import best_rank
from wowforever.schema import ClassData, SpellRank
from wowforever.toml_cache import load_toml

CONFIG = Path(__file__).resolve().parents[3] / "config" / "pvp_self.toml"
STOPS_ATTACKS = ("stun", "incapacitate", "disorient", "fear")


def thorns_dps(thorns: SpellRank | None, spell_power: float, coefficient: float, hits_per_second: float) -> float:
    """Damage per second Thorns returns to a melee attacker (#265): (base + coefficient x spell power) per hit."""
    if thorns is None or thorns.damage_shield <= 0:
        return 0.0
    return (thorns.damage_shield + coefficient * spell_power) * hits_per_second


def heal_modifiers(spell: SpellRank, cls: ClassData, ranks: Mapping[int, int]) -> tuple[float, float, float]:
    """(cast time change in s, mana cost %, healing %) from taken talents for one heal (#276).

    Cast time and mana cost come only from effects naming the heal (Moonglow's school-wide cut is for
    damaging spells); healing % from every `healing_pct` effect."""
    cast = cost = healing = 0.0
    for talent_id, rank in ranks.items():
        if rank <= 0:
            continue
        for effect in cls.talent(talent_id).effects:
            value = effect.values[rank - 1]
            if effect.kind == "healing_pct":
                healing += value
            elif spell.name in effect.applies_to and effect.kind == "cast_time":
                cast += value
            elif spell.name in effect.applies_to and effect.kind == "mana_cost_pct":
                cost += value
    return cast, cost, healing


def heal_capacity(class_name: str, stats, spells: Sequence[SpellRank], cls: ClassData,
                  ranks: Mapping[int, int]) -> tuple[float, float]:
    """(healing per second while healing, mana-limited healing budget) from the class's direct heals (#265).

    Each heal in config `heals` (best rank learned at the stats' level) heals its average direct amount plus
    heal coefficient x the build's spell power per cast of max(GCD, cast time) seconds; talents change cast time,
    mana cost and healing (heal_modifiers, #276); the best per second is used, and the budget is mana x
    heal_mana_share x its healing per mana. Classes without `heals`: (0, 0)."""
    cfg = load_toml(CONFIG)[class_name]
    if "heals" not in cfg:
        return (0.0, 0.0)
    row = build_stats(class_name, stats, cls, ranks)
    sp = getattr(row, "spell_power", 0.0)
    best: tuple[float, float, float] | None = None
    for name in cfg["heals"]:
        spell = best_rank(spells, name, stats.level)
        if spell is None or spell.mana_cost <= 0 or spell.heal_max <= 0:
            continue
        cast, cost, healing = heal_modifiers(spell, cls, ranks)
        amount = ((spell.heal_min + spell.heal_max) / 2 + spell.heal_coefficient * sp) * (1 + healing / 100)
        seconds = max(GCD_SECONDS, spell.cast_time + cast)
        mana = spell.mana_cost * (1 + cost / 100)
        if best is None or amount / seconds > best[0] / best[1]:
            best = (amount, seconds, mana)
    if best is None:
        return (0.0, 0.0)
    amount, seconds, mana = best
    return (amount / seconds, row.mana * cfg["heal_mana_share"] * amount / mana)


def class_side(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
               ranks: Mapping[int, int], *, assumptions: Assumptions | None = None) -> MageSide:
    """The class's duel side, in the same shape as the mage's."""
    if assumptions is None:
        assumptions = Assumptions.load()
    raw = load_toml(CONFIG)
    cfg = raw[class_name]
    taken = {t.name for t in cls.talents if ranks.get(t.talent_id, 0) > 0}
    controls = [Control(c["kind"], float(c["duration"]), float(c["cooldown"]), float(c.get("energy", 0.0)))
                for c in cfg["controls"] if c.get("requires") is None or c["requires"] in taken]
    locks = lockout_seconds(controls, cfg.get("energy_per_minute", 0.0))
    output = rotation_output(class_name, stats, spells, cls, ranks, Target(0, raw["player_armor"]))
    slow = cfg.get("slow", 0.0)
    if class_name == "hunter":
        from wowforever.classes.hunter_rotation import hunter_rotation
        from wowforever.melee_scenarios import _has_pet

        mode = hunter_rotation(stats, spells, cls, ranks, Target(0, raw["player_armor"]),
                               pet=_has_pet(cls, ranks)).mode
        slow = cfg["slow_melee"] if mode == "melee" else cfg["slow_ranged"]
    row = build_stats(class_name, stats, cls, ranks)
    thorns = thorns_dps(best_rank(spells, "Thorns", stats.level), getattr(row, "spell_power", 0.0),
                        assumptions["thorns_spell_power_coefficient"], raw.get("opponent_melee_hits_per_second", 0.0))
    heal_hps, heal_budget = heal_capacity(class_name, stats, spells, cls, ranks)
    return MageSide(
        health=row.health,
        dps=output.dps,
        nova_dps=thorns,
        barrier_per_min=0.0,
        immunity_share=0.0,
        # roots don't stop casting, so lockout_seconds skips them; they're kiting time vs melee
        root=min(60.0, sum(c.duration * 60 / c.cooldown for c in controls if c.kind == "root" and c.cooldown > 0)),
        stun=sum(locks.get(kind, 0.0) for kind in STOPS_ATTACKS),
        slow=slow,
        interrupt=locks.get("interrupt", 0.0) + locks.get("silence", 0.0),
        physical_taken=(armor_factor(stats.level, raw["own_armor"][class_name])
                        / armor_factor(stats.level, raw["cloth_armor"])),
        heal_hps=heal_hps,
        heal_budget=heal_budget,
    )


def pvp_score(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
              ranks: Mapping[int, int], kits: Sequence[Kit]) -> float:
    """Mean duel score over the four world-PvP scenarios (as the mage's, without battlegrounds)."""
    side = class_side(class_name, stats, spells, cls, ranks)
    scores = scenario_scores(side, kits)
    return sum(scores[s]["score"] for s in PVP_SCENARIOS) / len(PVP_SCENARIOS)
