"""Rogue, hunter and warrior PvP scores (#134, #162): the mage's duel model (#26, #121) from their side.

The class's side has the same fields as the mage's: health, rotation DPS against player armor, and
what its controls do to the opponent (stuns keep a melee opponent from hitting, interrupts lock a
caster, slows help kiting). Its own controls get the same energy budget and diminishing returns as
opponent kits (config/pvp_self.toml). The score is the mean over the four world-PvP scenarios.

Opponent kits' DPS assumes cloth; physical kits hit these classes by their armor ratio.
Not modeled yet: openers from stealth, Evasion, Vanish, Deterrence and Feign Death.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path

from wowforever.focus import PVP_SCENARIOS
from wowforever.melee_scenarios import rotation_output
from wowforever.melee_stats import MeleeStats
from wowforever.physical import Target, armor_factor
from wowforever.pvp.duel import Control, Kit, MageSide, lockout_seconds, scenario_scores
from wowforever.schema import ClassData, SpellRank

CONFIG = Path(__file__).resolve().parents[3] / "config" / "pvp_self.toml"
STOPS_ATTACKS = ("stun", "incapacitate", "disorient", "fear")


def class_side(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
               ranks: Mapping[int, int]) -> MageSide:
    """The class's duel side, in the same shape as the mage's."""
    raw = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
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
    return MageSide(
        health=stats.health,
        dps=output.dps,
        barrier_per_min=0.0,
        immunity_share=0.0,
        # roots don't stop casting, so lockout_seconds skips them; they're kiting time vs melee
        root=min(60.0, sum(c.duration * 60 / c.cooldown for c in controls if c.kind == "root" and c.cooldown > 0)),
        stun=sum(locks.get(kind, 0.0) for kind in STOPS_ATTACKS),
        slow=slow,
        interrupt=locks.get("interrupt", 0.0) + locks.get("silence", 0.0),
        physical_taken=(armor_factor(stats.level, raw["own_armor"][class_name])
                        / armor_factor(stats.level, raw["cloth_armor"])),
    )


def pvp_score(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
              ranks: Mapping[int, int], kits: Sequence[Kit]) -> float:
    """Mean duel score over the four world-PvP scenarios (as the mage's, without battlegrounds)."""
    side = class_side(class_name, stats, spells, cls, ranks)
    scores = scenario_scores(side, kits)
    return sum(scores[s]["score"] for s in PVP_SCENARIOS) / len(PVP_SCENARIOS)
