# Task #391 (part 2A): a dual-wield warrior stat table

Make `tests/test_warrior_dw_table.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order. Step 4 runs a command that writes `config/stats/warrior_dw.csv`; run it
  exactly once, after steps 1-3. It reads the cached client tables; it makes no network requests.
- Before you start, the tests in `tests/test_warrior_dw_table.py` fail.

## Why
Fury warriors dual wield, but the warrior's stat table picks a two-hander for every level. A second table,
`warrior_dw`, picks a main hand and an off hand from the same one-hand weapon types with the same armor and weights.
Part B (a later task) uses it for Fury builds.

## Step 1: `config/melee.toml`
1. In the `[warrior]` section, the comment `# Arms swings a two-hander (#162); Fury dual wield isn't modeled yet`
   becomes `# Arms swings a two-hander (#162); Fury builds use [warrior_dw] (#391)`.
2. Directly after the whole `[warrior.weights]` table (after its `weapon_dps = 3.0` line, before the blank line and
   `[paladin]`), add a blank line and this section:
```toml
[warrior_dw]
# Fury dual wield (#391): the [warrior] gear rules with a main hand and an off hand instead of a two-hander
armor = [[1, [1, 2, 3]], [40, [1, 2, 3, 4]]]
# 0 axe, 4 mace, 7 sword, 13 fist, 15 dagger
one_hand = [0, 4, 7, 13, 15]
two_hand = [1, 5, 6, 8]
ranged = [2, 3, 16, 18]
ap_level = 3
ap_str = 2
ap_agi = 0
ap_const = 20
rap_level = 1
rap_agi = 1
rap_const = 10
agi_per_crit_at_60 = 20.0
uses_mana = false
[warrior_dw.weights]
strength = 1.0
agility = 0.5
attack_power = 0.5
crit_rating = 1.0
hit_rating = 1.2
stamina = 0.3
weapon_dps = 3.0
```

## Step 2: `config/stats/warrior_dw_base.csv`
Create it as an exact copy of `config/stats/warrior_base.csv` (same base stats; only the gear differs).

## Step 3: `src/wowforever/__main__.py`
In the `gs.add_argument("--class", ...)` choices tuple, add `"warrior_dw"` after `"shaman_melee"`.

## Step 4: run it
`.venv/Scripts/python -m wowforever gear-stats --tables data/cache/wago/1.60.1.70425 --class warrior_dw`
It prints `wrote ...warrior_dw.csv`.

Nothing else changes.

## Done when
- `tests/test_warrior_dw_table.py` passes; `config/stats/warrior.csv` is unchanged; the fast suite has no new
  failures.
