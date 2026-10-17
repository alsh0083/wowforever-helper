# Task #392/#395/#396: execute-phase talents averaged over the fight

Make `tests/test_execute_talents.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order; run the test file at the end, then the fast suite once. Rogue, priest
  and warlock regression pins (`tests/test_dungeon_mana.py`, `tests/test_dot_mana.py`'s dungeon values,
  `tests/test_kit_stats.py`, opponent kits) may move; Claude re-derives them.
- Before you start, every test in `tests/test_execute_talents.py` fails.

## Why
Quietus, Early Demise and Decimation give a bonus only while the target is below a health threshold. With steady
damage a target spends N% of the fight below N% health, so the model counts each bonus at N% of its value
(best effort, owner OK 2026-10-16). `EffectRule.combine` already turns several captured numbers into one value.

## Step 1: `src/wowforever/classes/__init__.py`
Add this function directly after the `EffectRule` class (two blank lines before and after):
```python
def below_health(match: Match[str]) -> float:
    """A bonus that holds below a health threshold, averaged over the fight (#392): with steady damage the target
    spends N% of the fight below N% health, so the bonus counts at bonus x N / 100. The two captured numbers
    multiply, so their order in the rank text doesn't matter."""
    return float(match.group(1)) * float(match.group(2)) / 100
```

## Step 2: rules (each file imports `below_health` from `wowforever.classes` next to `EffectRule`)
1. `src/wowforever/classes/rogue.py`, `TALENT_EFFECTS`:
```python
    "Quietus": (
        EffectRule("damage_pct",
                   r"abilities cause (\d+(?:\.\d+)?)% more damage against targets below (\d+(?:\.\d+)?)% health",
                   ("Sinister Strike", "Ghostly Strike", "Hemorrhage"), combine=below_health),
    ),
```
   and delete the `UNMODELED` line for `"Quietus"`.
2. `src/wowforever/classes/priest.py`, `TALENT_EFFECTS`:
```python
    "Early Demise": (
        EffectRule("crit_chance", r"targets at or below (\d+(?:\.\d+)?)% health by (\d+(?:\.\d+)?)%",
                   ("Shadow Word: Death",), combine=below_health),
    ),
```
   and delete the `UNMODELED` line for `"Early Demise"`.
3. `src/wowforever/classes/warlock.py`, `TALENT_EFFECTS`:
```python
    # the Shadow Bolt and Searing Pain part; Soul Fire isn't in the rotation (#396)
    "Decimation": (
        EffectRule("damage_pct", r"enemy below (\d+(?:\.\d+)?)% health, they deal (\d+(?:\.\d+)?)% increased damage",
                   ("Shadow Bolt", "Searing Pain"), combine=below_health),
    ),
```
   and delete the `UNMODELED` line for `"Decimation"`.

Find how each class module imports `EffectRule` (for example `from wowforever.classes import EffectRule`) and add
`below_health` to that same import.

Nothing else changes.

## Done when
- `tests/test_execute_talents.py` passes (4 tests); no other new failures apart from rogue, priest and warlock pins.
