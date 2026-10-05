# Task #129 (part 1): weapon damage from the client tables

Make `tests/test_weapons.py` pass without breaking the rest of the suite. Create `src/wowforever/weapons.py` and add the three ItemDamage tables to the wago table list. Do not edit the tests or fixtures.

## Why
Rogue and hunter damage needs each weapon's damage range and speed. The client doesn't store them on the item. Modern clients compute them from item-level tables: DPS = `ItemDamage<Kind>[ItemLevel].Quality_<OverallQualityID>`, then spread it over the swing by `DmgVariance`. Arcanite Reaper comes out at 153–256 at speed 3.8, exactly as Classic's tooltip. The other fixture weapons aren't verified in game, so the tests pin the formula, not Classic tooltips.

## 1. `src/wowforever/weapons.py`
```python
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
    def dps(self) -> float: ...   # (min + max) / 2 / speed

def load_weapons(tables: Tables) -> dict[int, Weapon]: ...
```
- Weapons are the `Item` rows with `ClassID == 2` whose ItemSparse row has `ItemDelay > 0`, excluding wands (`SubclassID == 19`) and fishing poles (`SubclassID == 20`).
- `kind` from `Item.InventoryType`: 13 → one_hand, 21 → main_hand, 22 → off_hand, 17 → two_hand, 15/25/26 → ranged.
- Table: two_hand → `ItemDamageTwoHand`; ranged → `ItemDamageRanged`; everything else → `ItemDamageOneHand`. Look up the row whose `ItemLevel` equals the item's `ItemLevel`, column `Quality_<OverallQualityID>`.
- `x = dps * speed`; `min_damage = floor(x * (1 - DmgVariance / 2))`; `max_damage = floor(x * (1 + DmgVariance / 2))`.
- Skip (don't fail on) items whose item level has no table row.

`Tables` is the `dict[str, list[dict[str, str]]]` returned by `wowforever.normalize.read_tables`.

## 2. Table list
Add `"ItemDamageOneHand"`, `"ItemDamageTwoHand"`, `"ItemDamageRanged"` to the table names that `sources/wago.py` downloads (its `TABLES` tuple), so update checks cache them.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_weapons.py` fails with `ModuleNotFoundError: No module named 'wowforever.weapons'`. That's the expected failure; creating the module is the task. Install nothing and ask for no elevation. Write files with `tools/apply_patch.py` (see AGENTS.md). Start with `src/wowforever/weapons.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_weapons.py`, then run the full suite once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
