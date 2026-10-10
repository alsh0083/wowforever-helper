"""Rogue and hunter stat tables from real gear (#129): base stats plus the best real Forever armor
and weapons the class can use, with Classic attack power and crit rules from config/melee.toml."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from wowforever.gear import (HEALTH_PER_STAMINA, MANA_PER_INT, Item, _interpolate_base, _read_base_rows, _usable,
                             best_set, crit_pct_from_rating, hit_pct_from_rating, set_totals, weighted)
from wowforever.weapons import Weapon
from wowforever.toml_cache import load_toml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "melee.toml"
STATS_DIR = ROOT / "config" / "stats"
WEAPON_SLOTS = ("main_hand", "off_hand", "two_hand", "ranged")


@dataclass(frozen=True)
class MeleeStats:
    level: int
    strength: float
    agility: float
    stamina: float
    intellect: float
    attack_power: float
    ranged_attack_power: float
    crit_pct: float
    ranged_crit_pct: float
    hit_pct: float
    health: float
    mana: float
    main_hand: tuple[int, int, float] | None    # (min, max, speed)
    off_hand: tuple[int, int, float] | None
    ranged: tuple[int, int, float] | None


def class_config(class_name: str) -> dict:
    """The class's section of config/melee.toml."""
    return load_toml(CONFIG)[class_name]


def _allowed_armor(cfg: Mapping, level: int) -> frozenset[int]:
    allowed: list[int] = []
    for from_level, subclasses in cfg["armor"]:
        if from_level <= level:
            allowed = subclasses
    return frozenset(allowed)


def _best_weapons(items: list[Item], weapons: Mapping[int, Weapon], level: int, max_quality: int,
                  cfg: Mapping) -> tuple[tuple[Weapon, Item] | None, ...]:
    """(main hand, off hand, ranged), each the best usable (weapon, item) or None."""
    weights = cfg["weights"]
    by_id = {item.item_id: item for item in items}
    usable = [(w, by_id[w.item_id]) for w in weapons.values()
              if w.item_id in by_id and by_id[w.item_id].required_level <= level
              and by_id[w.item_id].quality <= max_quality and _usable(by_id[w.item_id])]

    def best(kinds: set[str], subclasses: Iterable[int], exclude: int | None = None):
        options = [(w, i) for w, i in usable
                   if w.kind in kinds and w.subclass in subclasses and w.item_id != exclude]
        if not options:
            return None
        return min(options, key=lambda wi: (-(wi[0].dps * weights["weapon_dps"] + weighted(wi[1], weights)),
                                            wi[0].item_id))

    if cfg.get("prefer_two_hand"):
        return best({"two_hand"}, cfg["two_hand"]), None, best({"ranged"}, cfg["ranged"])
    main = best({"one_hand", "main_hand"}, cfg["one_hand"])
    off = best({"one_hand", "off_hand"}, cfg["one_hand"], exclude=main[0].item_id if main else None)
    ranged = best({"ranged"}, cfg["ranged"])
    return main, off, ranged


def melee_stat_table(class_name: str, items: list[Item], weapons: Mapping[int, Weapon],
                     levels: Iterable[int]) -> list[MeleeStats]:
    """Per-level stats for a melee or ranged class: base row + best armor + best weapons."""
    cfg = class_config(class_name)
    base_rows = _read_base_rows(STATS_DIR / f"{class_name}_base.csv")
    rows: list[MeleeStats] = []
    for level in levels:
        max_quality = 3 if level < 60 else 4
        armor_set = best_set(items, level, max_quality, weights=cfg["weights"],
                             armor=_allowed_armor(cfg, level))
        for slot in WEAPON_SLOTS:
            armor_set.pop(slot, None)
        chosen = _best_weapons(items, weapons, level, max_quality, cfg)
        totals = set_totals(armor_set)
        for pick in chosen:
            if pick is not None:
                for stat, value in pick[1].stats.items():
                    totals[stat] = totals.get(stat, 0) + value
        base = _interpolate_base(base_rows, level)
        strength = base["strength"] + totals.get("strength", 0)
        agility = base["agility"] + totals.get("agility", 0)
        stamina = base["stamina"] + totals.get("stamina", 0)
        intellect = base["intellect"] + totals.get("intellect", 0)
        crit = (agility / (cfg["agi_per_crit_at_60"] * level / 60)
                + crit_pct_from_rating(totals.get("crit_rating", 0), level))
        main, off, ranged = (None if pick is None else (pick[0].min_damage, pick[0].max_damage, pick[0].speed)
                             for pick in chosen)
        rows.append(MeleeStats(
            level=level, strength=strength, agility=agility, stamina=stamina, intellect=intellect,
            attack_power=(cfg["ap_level"] * level + cfg.get("ap_str", 1) * strength
                          + cfg.get("ap_agi", 1) * agility - cfg["ap_const"]
                          + totals.get("attack_power", 0)),
            ranged_attack_power=(cfg["rap_level"] * level + cfg["rap_agi"] * agility - cfg["rap_const"]
                                 + totals.get("ranged_attack_power", 0) + totals.get("attack_power", 0)),
            crit_pct=crit, ranged_crit_pct=crit,
            hit_pct=hit_pct_from_rating(totals.get("hit_rating", 0), level),
            health=base["base_health"] + HEALTH_PER_STAMINA * stamina,
            mana=(base["base_mana"] + MANA_PER_INT * intellect) if cfg["uses_mana"] else 0.0,
            main_hand=main, off_hand=off, ranged=ranged,
        ))
    return rows


COLUMNS = ("level", "strength", "agility", "stamina", "intellect", "attack_power", "ranged_attack_power",
           "crit_pct", "ranged_crit_pct", "hit_pct", "health", "mana", "mh_min", "mh_max", "mh_speed",
           "oh_min", "oh_max", "oh_speed", "ranged_min", "ranged_max", "ranged_speed")


def write_melee_csv(rows: Iterable[MeleeStats], path: Path) -> None:
    """One row per level; missing weapons are 0; floats rounded to 2 decimals."""
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(COLUMNS)
        for r in rows:
            weapons = [v for w in (r.main_hand, r.off_hand, r.ranged) for v in (w or (0, 0, 0))]
            values = [r.level, r.strength, r.agility, r.stamina, r.intellect, r.attack_power,
                      r.ranged_attack_power, r.crit_pct, r.ranged_crit_pct, r.hit_pct, r.health, r.mana, *weapons]
            writer.writerow(round(v, 2) if isinstance(v, float) else v for v in values)
