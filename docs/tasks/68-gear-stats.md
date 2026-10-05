# Task #68: placeholder stats from real Forever gear

Implement `src/wowforever/gear.py` so `tests/test_gear.py` passes. Do not edit tests, fixtures, `config/gear.toml` or `config/stats/mage_base.csv`. Standard library only, type hints, short docstrings. Uses `read_tables` and `wowforever.stats.Stats`.

## Items (`load_items(tables) -> list[Item]`)
Tables: `ItemSparse`, `Item`, `RandPropPoints` (fixture: `tests/fixtures/wago-1.60.1.70205-items`).
- `@dataclass(frozen=True) Item`: `item_id, name, item_level, required_level, quality, slot, stats: dict[str, int]`.
- Quality columns: 2 → `Good`, 3 → `Superior`, 4 → `Epic` (skip other qualities).
- Budget category by `InventoryType`: 0 = {1 head, 5 chest, 7 legs, 17 two-hand, 20 robe}; 1 = {3 shoulder, 6 waist, 8 feet, 10 hands, 12 trinket}; 2 = {2 neck, 9 wrist, 11 finger, 16 back, 14 shield, 23 held off-hand}; 3 = {13 one-hand, 21 main hand, 22 off-hand weapon}; 4 = {15 ranged, 25 thrown, 26 wand}.
- Stat value = `round(RandPropPoints[ItemLevel].<Quality>_<category> * StatPercentEditor_i / 10000)` for each `StatModifier_bonusStat_i` not in (-1, 0).
- Stat names: 5 intellect, 6 spirit, 7 stamina, 45 spell_power, 32 crit_rating, 31 hit_rating, 43 mp5; ignore the rest.
- `slot` names: head, neck, shoulder, back, chest (5 and 20), wrist, hands, waist, legs, feet, finger (11), trinket (12), main_hand (13, 21), off_hand (22, 23, 14), two_hand (17), ranged (15, 25, 26).
- `item_by_name(items, name)` -> the item (first match).

## Best set
- `SLOTS = ("head","neck","shoulder","back","chest","wrist","hands","waist","legs","feet","finger1","finger2","trinket1","trinket2","main_hand","off_hand","two_hand","ranged")`
- `WEIGHTS` from `config/gear.toml [weights]`; `weighted(item, weights)` = Σ weight × value.
- `best_set(items, level, max_quality) -> dict[str, Item]`: items with `required_level <= level` and `quality <= max_quality`; per slot the highest `weighted` (ties: lower item id). Fingers and trinkets: the best two **different** items into `finger1/finger2`, `trinket1/trinket2`. Weapons: compare the best `two_hand` against the best `main_hand` + best `off_hand` and keep only the higher total (either `two_hand`, or `main_hand` + `off_hand`). Empty slots are omitted.
- `set_totals(items_by_slot) -> dict[str, int]`: summed stats (missing stats 0).

## Ratings and the stat table
- `crit_pct_from_rating(rating, level)` = `rating / (rating_per_pct_at_60 * max(level - 8, 1) / 52)`; hit the same.
- `gear_stat_table(items, levels) -> list[Stats]`: for each level, base row from `config/stats/mage_base.csv` (interpolated like `StatTable`) + `best_set(items, level, max_quality=3 if level < 60 else 4)` totals:
  `intellect`, `spirit`, `stamina` = base + gear; `spell_power` = gear; `crit_pct` = base_crit_pct + intellect / (int_per_crit_pct_at_60 × (level-8)/52) + crit rating %; `hit_pct` = hit rating %; `mana` = base_mana + 15 × intellect; `health` = base_health + 10 × stamina.

Also add a CLI `python -m wowforever gear-stats [--dataset ...]`? **No**: just the functions; Claude wires it in.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
