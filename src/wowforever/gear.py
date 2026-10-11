"""Placeholder per-level stats from real Forever gear (#68).

Item stats are real client data: the RandPropPoints budget for the item's level,
quality, and slot category times the item's StatPercentEditor shares. Per-level rows
combine the mage base stat table with the best affordable set of items and the
derived-stat rules in `config/gear.toml`.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from wowforever.normalize import Tables
from wowforever.stats import Stats
from wowforever.toml_cache import load_section, load_toml

CONFIG = Path(__file__).resolve().parents[2] / "config" / "gear.toml"
MAGE_BASE = Path(__file__).resolve().parents[2] / "config" / "stats" / "mage_base.csv"

SLOTS = (
    "head", "neck", "shoulder", "back", "chest", "wrist", "hands", "waist",
    "legs", "feet", "finger1", "finger2", "trinket1", "trinket2",
    "main_hand", "off_hand", "two_hand", "ranged",
)

# InventoryType -> RandPropPoints budget category (0-4)
BUDGET_CATEGORY = {
    1: 0, 5: 0, 7: 0, 17: 0, 20: 0,
    3: 1, 6: 1, 8: 1, 10: 1, 12: 1,
    2: 2, 9: 2, 11: 2, 16: 2, 14: 2, 23: 2,
    13: 3, 21: 3, 22: 3,
    15: 4, 25: 4, 26: 4,
}

# InventoryType -> equip slot name
SLOT_NAMES = {
    1: "head", 2: "neck", 3: "shoulder", 16: "back", 5: "chest", 20: "chest",
    9: "wrist", 10: "hands", 6: "waist", 7: "legs", 8: "feet",
    11: "finger", 12: "trinket",
    13: "main_hand", 21: "main_hand", 22: "off_hand", 23: "off_hand", 14: "off_hand",
    17: "two_hand", 15: "ranged", 25: "ranged", 26: "ranged",
}

# bonusStat id -> stat name; everything else is ignored
STAT_NAMES = {
    3: "agility", 4: "strength", 38: "attack_power", 39: "ranged_attack_power",
    5: "intellect", 6: "spirit", 7: "stamina", 45: "spell_power",
    32: "crit_rating", 31: "hit_rating", 43: "mp5",
}

# OverallQualityID -> RandPropPoints column prefix
QUALITY_NAMES = {2: "Good", 3: "Superior", 4: "Epic"}

_raw = load_toml(CONFIG)
WEIGHTS: Mapping[str, float] = dict(_raw["weights"])
RATING_PER_PCT_AT_60 = float(_raw["rating_per_pct_at_60"])
MANA_PER_INT = float(_raw["mana_per_int"])
HEALTH_PER_STAMINA = float(_raw["health_per_stamina"])
BASE_CRIT_PCT = float(_raw["base_crit_pct"])
INT_PER_CRIT_PCT_AT_60 = float(_raw["int_per_crit_pct_at_60"])
MAX_EPIC_ITEM_LEVEL = int(_raw["max_epic_item_level"])
EXCLUDE_NAME_WORDS = tuple(w.lower() for w in _raw["exclude_name_words"])
MAX_ITEM_LEVEL_GAP = int(_raw["max_item_level_over_required"])


def _usable(item: Item) -> bool:
    """Not a client test item, and epics only up to the pre-raid item level."""
    words = item.name.lower().replace("+", " ").split()
    if any(w in words or item.name.lower().startswith(w) for w in EXCLUDE_NAME_WORDS):
        return False
    if item.item_level - item.required_level > MAX_ITEM_LEVEL_GAP:
        return False  # level-scaling items: their listed item level overstates them early on
    return item.quality < 4 or item.item_level <= MAX_EPIC_ITEM_LEVEL


@dataclass(frozen=True)
class Item:
    """A piece of gear with its levels, slot, and derived stats."""
    item_id: int
    name: str
    item_level: int
    required_level: int
    quality: int
    slot: str
    stats: dict[str, int]
    armor_type: int | None = None   # Item.SubclassID for armor (1 cloth, 2 leather, 3 mail, 4 plate)


def load_items(tables: Tables) -> list[Item]:
    """Items with a known quality, slot, and stats, from the wago item tables."""
    rand_points = {row["ID"]: row for row in tables["RandPropPoints"]}
    armor_types = {row["ID"]: int(row["SubclassID"]) for row in tables.get("Item", ())
                   if row["ClassID"] == "4"}
    items: list[Item] = []
    for row in tables["ItemSparse"]:
        quality = int(row["OverallQualityID"])
        inventory_type = int(row["InventoryType"])
        if quality not in QUALITY_NAMES or inventory_type not in BUDGET_CATEGORY:
            continue
        budget = float(rand_points[row["ItemLevel"]][
            f"{QUALITY_NAMES[quality]}_{BUDGET_CATEGORY[inventory_type]}"])
        stats: dict[str, int] = {}
        for i in range(10):
            stat_id = int(row[f"StatModifier_bonusStat_{i}"])
            if stat_id in (-1, 0) or stat_id not in STAT_NAMES:
                continue
            value = round(budget * int(row[f"StatPercentEditor_{i}"]) / 10000)
            if value:
                stats[STAT_NAMES[stat_id]] = stats.get(STAT_NAMES[stat_id], 0) + value
        items.append(Item(
            item_id=int(row["ID"]), name=row["Display_lang"],
            item_level=int(row["ItemLevel"]), required_level=int(row["RequiredLevel"]),
            quality=quality, slot=SLOT_NAMES[inventory_type], stats=stats,
            armor_type=armor_types.get(row["ID"]),
        ))
    return items


def item_by_name(items: list[Item], name: str) -> Item:
    """The first item named `name`."""
    for item in items:
        if item.name == name:
            return item
    raise KeyError(name)


def weighted(item: Item, weights: Mapping[str, float]) -> float:
    """Weighted value of an item: sum of weight * value over its stats."""
    return sum(weights.get(stat, 0.0) * value for stat, value in item.stats.items())


ANY_ARMOR_SLOTS = frozenset({"back", "neck", "finger", "trinket"})


def _wearable(item: Item, armor: frozenset[int] | None) -> bool:
    """Whether a class wearing armor subclasses `armor` can use `item` (None: no restriction)."""
    return (armor is None or item.armor_type in (None, 0) or item.armor_type in armor
            or item.slot in ANY_ARMOR_SLOTS)


def best_set(items: list[Item], level: int, max_quality: int, *,
             weights: Mapping[str, float] = WEIGHTS,
             armor: frozenset[int] | None = None) -> dict[str, Item]:
    """The best item per slot for a `level` character wearing quality <= max_quality.

    `armor` limits armor to those subclasses (cloaks, necks, rings and trinkets stay open). The two
    best different items fill finger1/finger2 and trinket1/trinket2; weapons keep only the better of
    two_hand and main_hand + off_hand.
    """
    by_slot: dict[str, list[Item]] = {}
    for item in items:
        if (item.required_level <= level and item.quality <= max_quality and _usable(item)
                and _wearable(item, armor)):
            by_slot.setdefault(item.slot, []).append(item)

    def rank(group: list[Item]) -> list[Item]:
        return sorted(group, key=lambda item: (-weighted(item, weights), item.item_id))

    result: dict[str, Item] = {}
    for slot, group in by_slot.items():
        if slot in ("finger", "trinket"):
            for key, item in zip((f"{slot}1", f"{slot}2"), rank(group)[:2]):
                result[key] = item
        else:
            result[slot] = rank(group)[0]

    two_hand = result.get("two_hand")
    main_hand, off_hand = result.get("main_hand"), result.get("off_hand")
    pair = main_hand is not None and off_hand is not None
    use_two = two_hand is not None and (
        not pair or weighted(two_hand, weights) >= weighted(main_hand, weights) + weighted(off_hand, weights))
    if use_two:
        result.pop("main_hand", None)
        result.pop("off_hand", None)
    elif pair:
        result.pop("two_hand", None)
    else:
        for slot in ("two_hand", "main_hand", "off_hand"):
            result.pop(slot, None)
    return result


def set_totals(items_by_slot: Mapping[str, Item]) -> dict[str, int]:
    """Total stats of a slot-to-item mapping (stats an item lacks count as 0)."""
    totals: dict[str, int] = {}
    for item in items_by_slot.values():
        for stat, value in item.stats.items():
            totals[stat] = totals.get(stat, 0) + value
    return totals


def _rating_pct(rating: float, level: int) -> float:
    return rating / (RATING_PER_PCT_AT_60 * max(level - 8, 1) / 52)


def crit_pct_from_rating(rating: float, level: int) -> float:
    """Spell crit percent for `rating` crit rating at `level` (scales by (level - 8)/52)."""
    return _rating_pct(rating, level)


def hit_pct_from_rating(rating: float, level: int) -> float:
    """Hit percent for `rating` hit rating at `level` (scales by (level - 8)/52)."""
    return _rating_pct(rating, level)


def gear_stat_table(items: list[Item], levels: Iterable[int]) -> list[Stats]:
    """Per-level mage stats: the interpolated base row plus the best gear set's stats."""
    base_rows = _read_base_rows()
    rows: list[Stats] = []
    for level in levels:
        base = _interpolate_base(base_rows, level)
        totals = set_totals(best_set(items, level, 3 if level < 60 else 4, armor=frozenset({1})))
        intellect = base["intellect"] + totals.get("intellect", 0)
        spirit = base["spirit"] + totals.get("spirit", 0)
        stamina = base["stamina"] + totals.get("stamina", 0)
        int_scaling = level / 60  # Intellect per 1% crit grows with level (an inference)
        rows.append(Stats(
            level=level,
            intellect=intellect,
            spirit=spirit,
            stamina=stamina,
            spell_power=float(totals.get("spell_power", 0)),
            crit_pct=(BASE_CRIT_PCT + intellect / (INT_PER_CRIT_PCT_AT_60 * int_scaling)
                      + crit_pct_from_rating(totals.get("crit_rating", 0), level)),
            hit_pct=hit_pct_from_rating(totals.get("hit_rating", 0), level),
            mana=base["base_mana"] + MANA_PER_INT * intellect,
            health=base["base_health"] + HEALTH_PER_STAMINA * stamina,
        ))
    return rows


def _read_base_rows(path: Path = MAGE_BASE) -> list[dict[str, float]]:
    """Base stat anchors from a `config/stats/<class>_base.csv` file (the mage's by default)."""
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            {key: (int(value) if key == "level" else float(value)) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def _interpolate_base(rows: list[dict[str, float]], level: int) -> dict[str, float]:
    """The base row at `level`, linearly interpolated between anchors; clamped outside."""
    ordered = sorted(rows, key=lambda row: row["level"])
    lo, hi = ordered[0], ordered[-1]
    if level <= lo["level"]:
        return lo
    if level >= hi["level"]:
        return hi
    for anchor, upper in zip(ordered, ordered[1:]):
        if anchor["level"] <= level <= upper["level"]:
            t = (level - anchor["level"]) / (upper["level"] - anchor["level"])
            return {key: anchor[key] + t * (upper[key] - anchor[key]) for key in anchor}
    raise AssertionError("unreachable")


CASTERS = Path(__file__).resolve().parents[2] / "config" / "casters.toml"


def caster_config(class_name: str) -> dict:
    """The class's section of config/casters.toml (#163)."""
    return load_section(CASTERS, class_name)


def caster_stat_table(class_name: str, items: list[Item], levels: Iterable[int]) -> list[Stats]:
    """Per-level stats for a non-mage caster (#163): its base row plus the best gear it can wear,
    with its own crit and armor rules from config/casters.toml."""
    cfg = caster_config(class_name)
    base_rows = _read_base_rows(MAGE_BASE.parent / f"{class_name}_base.csv")
    rows: list[Stats] = []
    for level in levels:
        allowed: list[int] = []
        for from_level, subclasses in cfg["armor"]:
            if from_level <= level:
                allowed = subclasses
        base = _interpolate_base(base_rows, level)
        totals = set_totals(best_set(items, level, 3 if level < 60 else 4,
                                     weights=cfg.get("weights", WEIGHTS), armor=frozenset(allowed)))
        intellect = base["intellect"] + totals.get("intellect", 0)
        spirit = base["spirit"] + totals.get("spirit", 0)
        stamina = base["stamina"] + totals.get("stamina", 0)
        rows.append(Stats(
            level=level, intellect=intellect, spirit=spirit, stamina=stamina,
            spell_power=float(totals.get("spell_power", 0)),
            crit_pct=(cfg["base_crit_pct"] + intellect / (cfg["int_per_crit_pct_at_60"] * level / 60)
                      + crit_pct_from_rating(totals.get("crit_rating", 0), level)),
            hit_pct=hit_pct_from_rating(totals.get("hit_rating", 0), level),
            mana=base["base_mana"] + MANA_PER_INT * intellect,
            health=base["base_health"] + HEALTH_PER_STAMINA * stamina,
        ))
    return rows
