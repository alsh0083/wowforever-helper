"""PvP and PvE focus scores for whole builds at max level (#28): the numbers the shortlist ranks by.

- PvP: mean of the four duel scenarios (#26) and the battleground score (#27), plus a consensus bonus for taking talents the
  sources rate core in PvP (#24).
- PvE: `melee_scenarios.pve_score`, the same for every class (#317).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from wowforever.consensus import Consensus
from wowforever.pvp.battleground import best_side_battleground
from wowforever.pvp.duel import Kit, best_scenario_scores
from wowforever.schema import ClassData

PVP_SCENARIOS = ("wpvp_melee", "wpvp_melee_they_open", "wpvp_caster", "stealth_ambush")
CONSENSUS_BONUS = 0.10          # added for taking every PvP-core talent; scaled by the share taken


def pvp_core_talents(consensus: Consensus, class_name: str = "mage") -> set[str]:
    """Talent names the class's consensus tiers rate core in any world-PvP scenario."""
    tiers = consensus.tiers_for(class_name)
    return {name for scenario in ("wpvp_melee", "wpvp_caster", "stealth_ambush")
            for name in tiers.get(scenario, {}).get("core", ())}


def core_talent_ids(cls: ClassData, consensus: Consensus, class_name: str = "mage") -> set[int]:
    """Talent ids of the class's PvP-core talents (#320); empty for a class without tiers."""
    return {cls.talent_named(n).talent_id for n in pvp_core_talents(consensus, class_name)
            if any(t.name == n for t in cls.talents)}


def pvp_core_line(cls: ClassData, consensus: Consensus, class_name: str,
                  ranks: Mapping[int, int]) -> dict | None:
    """The class's community core PvP talents as the dashboard's own line (#341): taken and missing
    names, alphabetized, plus the consensus bonus for the share taken; None for a class without
    core talents."""
    names = [n for n in pvp_core_talents(consensus, class_name)
             if any(t.name == n for t in cls.talents)]
    if not names:
        return None
    taken = {n for n in names if ranks.get(cls.talent_named(n).talent_id, 0) > 0}
    return {"taken": sorted(taken), "missing": sorted(set(names) - taken),
            "bonus": round(CONSENSUS_BONUS * len(taken) / len(names), 3)}


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


def class_pvp_score(class_name: str, stats, cls: ClassData, ranks: Mapping[int, int], kits: Sequence[Kit],
                    consensus: Consensus) -> float:
    """Any class's PvP score (#323): `side_pvp_score` with its engine's duel side at `stats`' level."""
    from wowforever.classes import engine

    sides = engine(class_name).sides(stats, cls.spells, cls, ranks)
    return side_pvp_score(sides, kits, stats.level, core_talent_ids(cls, consensus, class_name), ranks, consensus)
