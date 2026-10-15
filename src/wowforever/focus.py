"""PvP and PvE focus scores for whole builds at max level (#28): the numbers the shortlist ranks by.

- PvP: mean of the four duel scenarios (#26) and the battleground score (#27), plus a consensus bonus for taking talents the
  sources rate core in PvP (#24).
- PvE: questing kills/hour, sustained raid DPS, 3-mob AoE speed and dungeon-pull DPS, each divided by a fixed
  reference and averaged. Scores are only compared within one shortlist slot, so fixed
  references are enough.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from wowforever import group
from wowforever.assumptions import Assumptions
from wowforever.consensus import Consensus
from wowforever.pvp.battleground import best_side_battleground
from wowforever.classes.mage import duel_side
from wowforever.pvp.duel import Kit, best_scenario_scores
from wowforever.scenarios import (Character, aoe_curve, default_params, questing, raid,
                                  usable_fillers)
from wowforever.schema import ClassData
from wowforever.stats import Stats

PVP_SCENARIOS = ("wpvp_melee", "wpvp_melee_they_open", "wpvp_caster", "stealth_ambush")
CONSENSUS_BONUS = 0.10          # added for taking every PvP-core talent; scaled by the share taken
PVE_REFERENCES = {"questing": 100.0, "raid": 150.0, "aoe_seconds_3": 15.0, "dungeon": 150.0}

ScoreFn = Callable[[Mapping[int, int]], float]


def pvp_core_talents(consensus: Consensus, class_name: str = "mage") -> set[str]:
    """Talent names the class's consensus tiers rate core in any world-PvP scenario."""
    tiers = consensus.tiers_for(class_name)
    return {name for scenario in ("wpvp_melee", "wpvp_caster", "stealth_ambush")
            for name in tiers.get(scenario, {}).get("core", ())}


def core_talent_ids(cls: ClassData, consensus: Consensus, class_name: str = "mage") -> set[int]:
    """Talent ids of the class's PvP-core talents (#320); empty for a class without tiers."""
    return {cls.talent_named(n).talent_id for n in pvp_core_talents(consensus, class_name)
            if any(t.name == n for t in cls.talents)}


def side_pvp_score(sides, kits: Sequence[Kit], level: int, core: set[int], ranks: Mapping[int, int],
                   consensus: Consensus) -> float:
    """The PvP score of any class (#315, option 1; #323): the mean of the four world-PvP duels and the
    battleground, each with the build's best side, plus CONSENSUS_BONUS x the share of the class's core
    talents taken (0 for a class without tiers)."""
    duels = best_scenario_scores(sides, kits)
    values = [duels[s]["score"] for s in PVP_SCENARIOS]
    values.append(best_side_battleground(sides, level, consensus)["score"])
    taken = sum(1 for tid in core if ranks.get(tid, 0) > 0)
    return sum(values) / len(values) + CONSENSUS_BONUS * taken / max(1, len(core))


def pvp_score_fn(cls: ClassData, stats: Stats, assumptions: Assumptions, kits: list[Kit],
                 consensus: Consensus) -> ScoreFn:
    """The mage's PvP score: `side_pvp_score` with one side per usable filler, built at the max level
    whatever level `stats` is from."""
    core = core_talent_ids(cls, consensus)
    level = cls.rules.max_level

    def score(ranks: Mapping[int, int]) -> float:
        char = Character(level, stats, cls.spells, cls, dict(ranks))
        fillers = usable_fillers(char, default_params("questing", level).fillers, level, assumptions)
        sides = [(f.name, duel_side(char, f)) for f in fillers]
        return side_pvp_score(sides, kits, level, core, ranks, consensus)

    return score


def class_pvp_score(class_name: str, stats, cls: ClassData, ranks: Mapping[int, int], kits: Sequence[Kit],
                    consensus: Consensus) -> float:
    """Any other class's PvP score (#323): `side_pvp_score` with its engine's duel side at `stats`' level."""
    from wowforever.classes import engine

    sides = engine(class_name).sides(stats, cls.spells, cls, ranks)
    return side_pvp_score(sides, kits, stats.level, core_talent_ids(cls, consensus, class_name), ranks, consensus)


def pve_score_fn(cls: ClassData, stats: Stats, assumptions: Assumptions) -> ScoreFn:
    """Score = mean of questing/100, raid/150 and 15/AoE-seconds-for-3-mobs."""
    level = cls.rules.max_level
    q_params, a_params, r_params, d_params = (default_params(s, level)
                                              for s in ("questing", "aoe", "raid", "dungeon"))

    def score(ranks: Mapping[int, int]) -> float:
        char = Character(level, stats, cls.spells, cls, dict(ranks))
        q = questing(char, q_params, assumptions).score
        r = raid(char, r_params, assumptions).score
        aoe_time = aoe_curve(char, a_params, assumptions).details["aoe_time"][3]
        d = group.typical_dungeon_dps("mage", stats, cls, ranks)    # with a weighted 5-player group (#220)
        return (q / PVE_REFERENCES["questing"] + r / PVE_REFERENCES["raid"]
                + PVE_REFERENCES["aoe_seconds_3"] / aoe_time + d / PVE_REFERENCES["dungeon"]) / 4

    return score
