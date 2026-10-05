# Task #129 (part 2): rogue and hunter stat tables from real gear

Make `tests/test_melee_stats.py` pass without breaking the rest of the suite. Edit `src/wowforever/gear.py`, create `src/wowforever/melee_stats.py`, and extend the `gear-stats` command in `src/wowforever/__main__.py`. `config/melee.toml` and `config/stats/{rogue,hunter}_base.csv` are written already. Do not edit the tests or config.

## Why
Rogue and hunter damage (#130 on) needs per-level stats: strength, agility, attack power, crit, hit, health, mana, and the best main-hand, off-hand and ranged weapons. They're built the way #68 built the mage's: base stats plus the best real Forever gear the class can wear.

## 1. `gear.py`
- `STAT_NAMES` gains `3: "agility"`, `4: "strength"`, `38: "attack_power"`, `39: "ranged_attack_power"`.
- `Item` gains `armor_type: int | None = None`, as a new last field. `load_items` sets it from the `Item` table (join on `ID`): `SubclassID` when `ClassID == 4`, else None. Leave it None when the tables have no `Item` table.
- `best_set(items, level, max_quality, *, weights=WEIGHTS, armor=None)`:
  - `weights` replaces the module-level `WEIGHTS` wherever `best_set` ranks items.
  - With `armor` (a set of armor subclasses), keep only items whose `armor_type` is None, 0, or in `armor`, plus any item in the `back`, `neck`, `finger` or `trinket` slots.
  - Without `armor`, behaviour is unchanged.
- `gear_stat_table` (the mage) passes `armor=frozenset({1})`: mages wear cloth only.

## 2. `src/wowforever/melee_stats.py`
```python
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

def melee_stat_table(class_name: str, items: list[Item], weapons: dict[int, Weapon],
                     levels: Iterable[int]) -> list[MeleeStats]: ...
```
Per level, with `cfg = config/melee.toml[class_name]`:
1. **Quality cap:** `max_quality = 3 if level < 60 else 4`, as for the mage.
2. **Armor:** the allowed set is the last `[from_level, subclasses]` entry of `cfg.armor` whose `from_level <= level`.
3. **Armor set:** `best_set(items, level, max_quality, weights=cfg.weights, armor=allowed)`, minus the weapon slots `main_hand`, `off_hand`, `two_hand` and `ranged`.
4. **Weapons:** candidates are the `weapons` whose item (same `item_id` in `items`) has `required_level <= level` and `quality <= max_quality`.
   - Score = `weapon.dps * cfg.weights.weapon_dps + weighted(item, cfg.weights)`; ties go to the lower `item_id`.
   - Main hand: best candidate with kind `one_hand` or `main_hand` and subclass in `cfg.one_hand`.
   - Off hand: best remaining candidate with kind `one_hand` or `off_hand` and subclass in `cfg.one_hand`.
   - Ranged: best candidate with kind `ranged` and subclass in `cfg.ranged`.
   - A missing weapon is None.
5. **Totals:** `set_totals` of the armor set, plus the stats of the chosen weapons' items.
6. **Base row:** `config/stats/<class>_base.csv`, interpolated like `_interpolate_base`. Reuse it; generalize the reader to take a path.
7. **Stats:**
   - `strength`, `agility`, `stamina`, `intellect` = base + totals.
   - `attack_power = ap_level*level + strength + agility - ap_const + totals.attack_power`.
   - `ranged_attack_power = rap_level*level + rap_agi*agility - rap_const + totals.ranged_attack_power + totals.attack_power`.
   - `crit_pct = ranged_crit_pct = agility / (agi_per_crit_at_60 * level / 60) + crit_pct_from_rating(totals.crit_rating, level)`.
   - `hit_pct = hit_pct_from_rating(totals.hit_rating, level)`.
   - `health = base_health + HEALTH_PER_STAMINA * stamina`.
   - `mana = base_mana + MANA_PER_INT * intellect` if `cfg.uses_mana`, else 0.
   - Weapons are stored as `(min_damage, max_damage, speed)`.

Also `write_melee_csv(rows, path)`: one row per level with columns level, strength, agility, stamina, intellect, attack_power, ranged_attack_power, crit_pct, ranged_crit_pct, hit_pct, health, mana, mh_min, mh_max, mh_speed, oh_min, oh_max, oh_speed, ranged_min, ranged_max, ranged_speed. Missing weapons are 0. Round floats to 2 decimals.

## 3. CLI
`python -m wowforever gear-stats --tables <folder> [--class mage|rogue|hunter]` (default mage, which writes `config/stats/mage.csv` as now). For rogue and hunter it loads `load_items` and `weapons.load_weapons` from the same folder and writes `config/stats/<class>.csv` with `write_melee_csv` for levels 10, 20, 30, 40, 50, 60.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_melee_stats.py` fails with `ModuleNotFoundError: No module named 'wowforever.melee_stats'`. That's the expected failure. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Start with `gear.py`, then `melee_stats.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_melee_stats.py tests/test_gear.py`, then run the full suite once at the end. Don't run the CLI; Claude regenerates the CSVs. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
