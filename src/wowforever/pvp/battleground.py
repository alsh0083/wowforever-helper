"""Battleground score (#27): group fights scored by the consensus axis weights (#24).

Battlegrounds aren't duels: there's no single opponent to race. The score weighs the build's
four axes with the consensus `battleground` weights (kill, endurance, survival, control):
- kill: rotation DPS (no sustained buffs) / KILL_REFERENCE, scaled by level / 60
- endurance: seconds until out of mana / ENDURANCE_SECONDS (capped at 1)
- survival, control: the #25 axis scores
Confidence: low (consensus weights are low confidence for battlegrounds).
"""

from __future__ import annotations

from wowforever.assumptions import Assumptions
from wowforever.calc.pvp_axes import control, survival
from wowforever.classes.mage_rotation import rotation
from wowforever.consensus import Consensus
from wowforever.scenarios import Character
from wowforever.schema import SpellRank

KILL_REFERENCE = 250.0      # DPS that counts as full kill pressure at level 60
ENDURANCE_SECONDS = 120.0   # a long battleground fight before drinking


def battleground(char: Character, filler: SpellRank, assumptions: Assumptions,
                 consensus: Consensus | None = None) -> dict:
    """{"score", "components": {"kill", "endurance", "survival", "control"}}, each component 0-1."""
    weights = (consensus or Consensus.load()).scenarios["battleground"].mid()
    rot = rotation(char, filler, target_level=char.level, assumptions=assumptions, sustained=False)
    kill = min(1.0, rot.dps / (KILL_REFERENCE * char.level / 60))
    drain = rot.mana_per_second
    endurance = 1.0 if drain <= 0 else min(1.0, char.stats.mana / drain / ENDURANCE_SECONDS)
    components = {"kill": kill, "endurance": endurance,
                  "survival": survival(char, filler).score, "control": control(char, filler).score}
    return {"score": sum(weights[k] * v for k, v in components.items()), "components": components}
