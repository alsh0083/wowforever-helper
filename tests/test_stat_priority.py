"""Stat priority per build for the dashboard (#292).

stat_weights.stat_priority ranks item-budget stats (Strength, Agility, Stamina, Intellect, Spirit, attack
power, spell power, crit and hit rating) by weight per point, with each stat's share of the top stat. A stat
joins the tier of the stat that opened it while its share is within 0.05 of that stat's; stats under 0.05 of
the top are dropped; "+N%" equip effects and weapon DPS aren't ranked. Hand-worked:
  spell power 0.002 -> 1.0 tier 1; hit rating 0.0019 -> 0.95 tier 1 (0.05 below the tier's lead);
  crit rating 0.0012 -> 0.6 tier 2; Intellect 0.0004 -> 0.2 tier 3; Stamina 0.00005 -> 0.025 dropped;
  Spirit 0 and crit_pct ignored.
report._stat_priority: endgame builds at 60 from their focus (PvP duels / PvE score), leveling builds at 40
from questing pace, builds without an engine score from the class's generic weights.
"""

from wowforever.report import _stat_priority
from wowforever.stat_weights import stat_priority

WEIGHTS = {"score": 0.5, "spell_power": 0.002, "hit_rating": 0.0019, "crit_rating": 0.0012, "intellect": 0.0004,
           "stamina": 0.00005, "spirit": 0.0, "crit_pct": 0.01, "weapon_dps": 0.5}


def test_stats_rank_into_tiers():
    assert stat_priority(WEIGHTS) == [
        {"stat": "spell_power", "share": 1.0, "tier": 1},
        {"stat": "hit_rating", "share": 0.95, "tier": 1},
        {"stat": "crit_rating", "share": 0.6, "tier": 2},
        {"stat": "intellect", "share": 0.2, "tier": 3},
    ]


def test_no_positive_weights_give_no_list():
    assert stat_priority({"score": 0.4, "spell_power": 0.0, "stamina": -0.001}) == []


def test_each_build_gets_its_level_and_basis():
    by_level = {"40": WEIGHTS, "60": {**WEIGHTS, "stamina": 0.003}}
    pvp = _stat_priority({"stat_weights": by_level, "mode": "endgame"}, "PvP")
    assert (pvp["level"], pvp["basis"], pvp["stats"][0]["stat"]) == (60, "PvP duels", "stamina")
    pve = _stat_priority({"stat_weights": by_level, "mode": "endgame"}, "PvE")
    assert pve["basis"] == "PvE score"
    leveling = _stat_priority({"stat_weights": by_level, "mode": "leveling"}, "PvE")
    assert (leveling["level"], leveling["basis"], leveling["stats"][0]["stat"]) == (40, "questing pace", "spell_power")
    generic = _stat_priority({"stat_weights": {"generic": {"spell_power": 1.0, "intellect": 0.4}}}, "PvE")
    assert generic["level"] is None and generic["basis"] == "class default, not from the model"
    assert [s["stat"] for s in generic["stats"]] == ["spell_power", "intellect"]
