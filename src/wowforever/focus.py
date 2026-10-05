"""PvP and PvE focus scores for whole builds at max level (#28): the numbers the shortlist ranks by.

- PvP: mean of the four duel scenarios (#26) and the battleground score (#27), plus a consensus bonus for taking talents the
  sources rate core in PvP (#24).
- PvE: questing kills/hour, sustained raid DPS, 3-mob AoE speed and dungeon-pull DPS, each divided by a fixed
  reference and averaged. Scores are only compared within one shortlist slot, so fixed
  references are enough.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from wowforever.assumptions import Assumptions
from wowforever.consensus import Consensus
from wowforever.pvp.battleground import battleground
from wowforever.pvp.duel import Kit, mage_side, scenario_scores
from wowforever.scenarios import Character, aoe_curve, best_rank, default_params, questing, raid
from wowforever.schema import ClassData, SpellRank
from wowforever.stats import Stats

PVP_SCENARIOS = ("wpvp_melee", "wpvp_melee_they_open", "wpvp_caster", "stealth_ambush")
CONSENSUS_BONUS = 0.10          # added for taking every PvP-core talent; scaled by the share taken
PVE_REFERENCES = {"questing": 100.0, "raid": 150.0, "aoe_seconds_3": 15.0, "dungeon": 150.0}

ScoreFn = Callable[[Mapping[int, int]], float]


def pvp_core_talents(consensus: Consensus) -> set[str]:
    """Talent names the consensus tiers rate core in any world-PvP scenario."""
    return {name for scenario in ("wpvp_melee", "wpvp_caster", "stealth_ambush")
            for name in consensus.tiers.get(scenario, {}).get("core", ())}


def _filler(char: Character, assumptions: Assumptions) -> SpellRank:
    q = questing(char, default_params("questing", char.level), assumptions)
    return best_rank(char.spells, q.details["spell"], char.level)


def pvp_score_fn(cls: ClassData, stats: Stats, assumptions: Assumptions, kits: list[Kit],
                 consensus: Consensus) -> ScoreFn:
    """Score = mean duel score over the PvP scenarios + share of core talents x CONSENSUS_BONUS."""
    core = {cls.talent_named(n).talent_id for n in pvp_core_talents(consensus)
            if any(t.name == n for t in cls.talents)}
    level = cls.rules.max_level

    def score(ranks: Mapping[int, int]) -> float:
        char = Character(level, stats, cls.spells, cls, dict(ranks))
        duels = scenario_scores(mage_side(char, _filler(char, assumptions)), kits)  # duels
        filler = _filler(char, assumptions)
        scenario_values = [duels[s]["score"] for s in PVP_SCENARIOS]
        scenario_values.append(battleground(char, filler, assumptions)["score"])
        mean = sum(scenario_values) / len(scenario_values)
        taken = sum(1 for tid in core if ranks.get(tid, 0) > 0)
        return mean + CONSENSUS_BONUS * taken / max(1, len(core))

    return score


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
        d = raid(char, d_params, assumptions).score
        return (q / PVE_REFERENCES["questing"] + r / PVE_REFERENCES["raid"]
                + PVE_REFERENCES["aoe_seconds_3"] / aoe_time + d / PVE_REFERENCES["dungeon"]) / 4

    return score
