"""Weapon damage from the client's ItemDamage tables (#129).

Modern clients store no damage on the item itself: the item-level table
(`ItemDamageOneHand` / `ItemDamageTwoHand` / `ItemDamageRanged`) gives the
weapon's DPS at its item level and quality, and `DmgVariance` spreads that
DPS over the swing (`ItemDelay` / 1000 seconds). Arcanite Reaper works out
to 153-256 at speed 3.8, matching its Classic tooltip.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from wowforever.normalize import Tables

# Item.SubclassID of wands and fishing poles: no weapon damage to model.
NO_DAMAGE_SUBCLASSES = frozenset({19, 20})

# Item.InventoryType -> Weapon.kind
KIND_BY_INVENTORY_TYPE = {13: "one_hand", 21: "main_hand", 22: "off_hand", 17: "two_hand"}
RANGED_INVENTORY_TYPES = frozenset({15, 25, 26})

# Weapon.kind -> client damage table
DAMAGE_TABLE_BY_KIND = {
    "one_hand": "ItemDamageOneHand",
    "main_hand": "ItemDamageOneHand",
    "off_hand": "ItemDamageOneHand",
    "two_hand": "ItemDamageTwoHand",
    "ranged": "ItemDamageRanged",
}


@dataclass(frozen=True)
class Weapon:
    item_id: int
    name: str
    kind: str          # "one_hand" | "main_hand" | "off_hand" | "two_hand" | "ranged"
    subclass: int      # Item.SubclassID (0 axe, 1 2H axe, 2 bow, 4 mace, 7 sword, 13 fist, 15 dagger, ...)
    min_damage: int
    max_damage: int
    speed: float       # seconds (ItemDelay / 1000)

    @property
    def dps(self) -> float:
        return (self.min_damage + self.max_damage) / 2 / self.speed


def load_weapons(tables: Tables) -> dict[int, Weapon]:
    """Weapons as `Item` rows with ClassID 2 and `ItemDelay` > 0, keyed by item id.

    Wands (SubclassID 19) and fishing poles (20) are excluded. The damage
    range spreads the table's DPS over the swing; items whose item level has
    no row in the table are skipped, not errors.
    """
    sparse = {row["ID"]: row for row in tables.get("ItemSparse", [])}
    levels = {
        (name, int(row["ItemLevel"])): row
        for name in set(DAMAGE_TABLE_BY_KIND.values())
        for row in tables.get(name, [])
    }
    weapons: dict[int, Weapon] = {}
    for item in tables.get("Item", []):
        if item["ClassID"] != "2":
            continue
        subclass = int(item["SubclassID"])
        if subclass in NO_DAMAGE_SUBCLASSES:
            continue
        inventory_type = int(item["InventoryType"])
        if inventory_type in RANGED_INVENTORY_TYPES:
            kind = "ranged"
        elif inventory_type in KIND_BY_INVENTORY_TYPE:
            kind = KIND_BY_INVENTORY_TYPE[inventory_type]
        else:
            continue
        row = sparse.get(item["ID"])
        if row is None or int(row["ItemDelay"]) <= 0:
            continue
        level_row = levels.get((DAMAGE_TABLE_BY_KIND[kind], int(row["ItemLevel"])))
        if level_row is None:
            continue
        dps = float(level_row[f"Quality_{row['OverallQualityID']}"])
        speed = int(row["ItemDelay"]) / 1000
        swing = dps * speed
        variance = float(row["DmgVariance"])
        item_id = int(item["ID"])
        weapons[item_id] = Weapon(
            item_id=item_id,
            name=row["Display_lang"],
            kind=kind,
            subclass=subclass,
            min_damage=math.floor(swing * (1 - variance / 2)),
            max_damage=math.floor(swing * (1 + variance / 2)),
            speed=speed,
        )
    return weapons
