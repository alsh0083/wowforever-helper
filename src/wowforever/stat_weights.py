"""Stat weights per build and level from the class's own engine (#189).

For each scored build at each checkpoint, one item stat at a time is raised by a small amount, carried
into the derived stats by the class's rules (Intellect -> mana and spell crit, Strength/Agility ->
attack power, ratings -> percentages, weapon DPS -> the main hand), and the build is re-scored with its
focus (PvE builds with the PvE score, PvP builds with the PvP score). The weight is the score change per
point, and the report also keeps the base score, so the dashboard can show an item's gain as a share
of the build's score without running an engine in the browser.

Healer and tank builds have no engine score; they get the class's generic gear weights (#190 shows
them as such).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any

from wowforever.gear import HEALTH_PER_STAMINA, MANA_PER_INT, crit_pct_from_rating, hit_pct_from_rating
from wowforever.schema import ClassData

# item stats the panel weighs; crit_pct/hit_pct are the site's "+N%" equip effects
STATS = ("strength", "agility", "stamina", "intellect", "spirit", "attack_power", "spell_power",
         "crit_rating", "hit_rating", "crit_pct", "hit_pct", "weapon_dps")
STEP = {"weapon_dps": 2.0, "crit_pct": 1.0, "hit_pct": 1.0}
DEFAULT_STEP = 10.0


def _caster_apply(class_name: str, stats, stat: str, amount: float):
    """A caster's Stats (mage format) with `amount` more of an item stat."""
    if class_name == "mage":
        from wowforever.gear import INT_PER_CRIT_PCT_AT_60 as ipc
    else:
        from wowforever.gear import caster_config

        ipc = caster_config(class_name)["int_per_crit_pct_at_60"]
    level = stats.level
    if stat == "intellect":
        return replace(stats, intellect=stats.intellect + amount, mana=stats.mana + MANA_PER_INT * amount,
                       crit_pct=stats.crit_pct + amount / (ipc * level / 60))
    if stat == "spirit":
        return replace(stats, spirit=stats.spirit + amount)
    if stat == "stamina":
        return replace(stats, stamina=stats.stamina + amount, health=stats.health + HEALTH_PER_STAMINA * amount)
    if stat == "spell_power":
        return replace(stats, spell_power=stats.spell_power + amount)
    if stat in ("crit_rating", "crit_pct"):
        pct = crit_pct_from_rating(amount, level) if stat == "crit_rating" else amount
        return replace(stats, crit_pct=stats.crit_pct + pct)
    if stat in ("hit_rating", "hit_pct"):
        pct = hit_pct_from_rating(amount, level) if stat == "hit_rating" else amount
        return replace(stats, hit_pct=stats.hit_pct + pct)
    return None                                   # strength, agility, attack power, weapons: no caster effect


def _melee_apply(cfg_name: str, stats, stat: str, amount: float):
    """A melee/ranged MeleeStats with `amount` more of an item stat, by config/melee.toml's rules."""
    from wowforever.melee_stats import class_config

    cfg = class_config(cfg_name)
    level = stats.level
    if stat in ("strength", "agility"):
        ap = cfg.get("ap_str", 1) if stat == "strength" else cfg.get("ap_agi", 1)
        rap = cfg.get("rap_agi", 0) if stat == "agility" else 0
        new = replace(stats, attack_power=stats.attack_power + ap * amount,
                      ranged_attack_power=stats.ranged_attack_power + rap * amount,
                      **{stat: getattr(stats, stat) + amount})
        if stat == "agility":
            crit = amount / (cfg["agi_per_crit_at_60"] * level / 60)
            new = replace(new, crit_pct=new.crit_pct + crit, ranged_crit_pct=new.ranged_crit_pct + crit)
        return new
    if stat == "stamina":
        return replace(stats, stamina=stats.stamina + amount, health=stats.health + HEALTH_PER_STAMINA * amount)
    if stat == "intellect":
        mana = MANA_PER_INT * amount if cfg.get("uses_mana") else 0.0
        return replace(stats, intellect=stats.intellect + amount, mana=stats.mana + mana)
    if stat == "attack_power":
        return replace(stats, attack_power=stats.attack_power + amount,
                       ranged_attack_power=stats.ranged_attack_power + amount)
    if stat in ("crit_rating", "crit_pct"):
        pct = crit_pct_from_rating(amount, level) if stat == "crit_rating" else amount
        return replace(stats, crit_pct=stats.crit_pct + pct, ranged_crit_pct=stats.ranged_crit_pct + pct)
    if stat in ("hit_rating", "hit_pct"):
        pct = hit_pct_from_rating(amount, level) if stat == "hit_rating" else amount
        return replace(stats, hit_pct=stats.hit_pct + pct)
    if stat == "weapon_dps" and stats.main_hand is not None:
        lo, hi, speed = stats.main_hand
        bonus = amount * speed
        return replace(stats, main_hand=(lo + bonus, hi + bonus, speed))
    return None


def apply(class_name: str, stats, stat: str, amount: float, *, melee_build: bool = False):
    """`stats` with `amount` more of `stat`, or None when the stat does nothing for this build."""
    from wowforever.melee_scenarios import HybridStats

    if isinstance(stats, HybridStats):
        if melee_build:
            inner = _melee_apply(f"{class_name}_melee", stats.melee, stat, amount)
            return None if inner is None else replace(stats, melee=inner)
        inner = _caster_apply(class_name, stats.caster, stat, amount)
        return None if inner is None else replace(stats, caster=inner)
    if hasattr(stats, "spell_power"):
        return _caster_apply(class_name, stats, stat, amount)
    return _melee_apply(class_name, stats, stat, amount)


def weights_at(class_name: str, stats, score: Callable[[Any], float], *, melee_build: bool = False) -> dict[str, float]:
    """{"score": base score, stat: score change per point, ...} for one build at one level."""
    base = score(stats)
    out = {"score": round(base, 4)}
    for stat in STATS:
        step = STEP.get(stat, DEFAULT_STEP)
        bumped = apply(class_name, stats, stat, step, melee_build=melee_build)
        if bumped is not None:
            out[stat] = round((score(bumped) - base) / step, 6)
    return out


def generic_weights(class_name: str) -> dict[str, float]:
    """The class's gear-picking weights (no engine score: healer and tank builds)."""
    from wowforever.classes import class_module

    if class_name == "mage":
        from wowforever.gear import WEIGHTS

        return dict(WEIGHTS)
    if getattr(class_module(class_name), "ENGINE", None) == "spell":
        from wowforever.gear import caster_config

        return dict(caster_config(class_name).get("weights", {}))
    from wowforever.melee_stats import class_config

    return dict(class_config(class_name).get("weights", {}))


def build_weights(class_name: str, cls: ClassData, build: Mapping[str, Any], table,
                  score_for: Callable[[Any, Mapping[int, int]], float], levels: Sequence[int],
                  *, melee_build: Callable[[Mapping[int, int]], bool] = lambda r: False) -> dict[str, dict[str, float]]:
    """Weights at each checkpoint level for one report build (its order gives the ranks at each level)."""
    from wowforever.report import ranks_at

    out = {}
    for level in levels:
        ranks = ranks_at(build["order"], level, cls)
        out[str(level)] = weights_at(class_name, table.at(level), lambda s: score_for(s, ranks),
                                     melee_build=melee_build(ranks))
    return out
