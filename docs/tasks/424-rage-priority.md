# Task #424: Overpower and Rend get Rage before the cooldown abilities

Make `tests/test_rage_priority.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/warrior_rotation.py`. Run the test file, then the fast suite
  once. Warrior regression pins (`tests/test_dungeon_mana.py` warrior-arms, `tests/test_kit_stats.py`, opponent
  kits) will move; Claude re-derives them.
- Before you start, `tests/test_rage_priority.py` fails, and so does `tests/test_warrior_aoe.py::
  test_single_target_is_unchanged` (it already expects the new order).
- This is a move of two existing blocks of code, not new logic. Do it as two small patches: first add the copy
  above the plan, then delete the old copy (see Step 2).

## Why
Rage is scarce for a two-hander. Overpower (5 Rage) and Rend (10 Rage per 21 s) do far more damage per Rage than
Mortal Strike, Whirlwind or Slam, so a player spends Rage on them first. Today they run after the cooldown abilities
and get nothing at 60 against a boss.

## Step 1: docstring
In the module docstring, the lines
```
joins the priority. Execute takes all Rage in the last 20% of the fight (#391). Overpower follows
dodges and Rend is kept up on one target (#391). Slam joins with Improved
Slam (#391). Not modeled yet: Rage from damage taken.
```
become
```
joins the priority. Execute takes all Rage in the last 20% of the fight (#391). Overpower follows
dodges and Rend is kept up on one target (#391); both get Rage before the cooldown abilities, as the most
damage per Rage (#424). Slam joins with Improved Slam (#391). Not modeled yet: Rage from damage taken.
```

## Step 2: move the Overpower and Rend blocks
In `warrior_rotation`, two blocks currently sit after the `for spell in plan:` loop:
- the Overpower block, from the line `    overpower = learned("Overpower")` through the line `            used.append("Overpower")`;
- the Rend block, from the line `    rend = learned("Rend")` through the line `        used.append("Rend")`.

Move both blocks, unchanged and in the same order (Overpower, then Rend), to directly before the line
```python
    names = ("Mortal Strike", "Bloodthirst", "Whirlwind", "Slam") + (("Thunder Clap",) if pack > 1 else ())
```
(so after the line `    single, attacks = 0.0, swings + oh_swings   # ...`), followed by one blank line. Then add
this comment line directly above `    overpower = learned("Overpower")` in its new place:
```python
    # Overpower and Rend first: the most damage per Rage (#424)
```
Leave everything else as it is. After the move, the `for spell in plan:` loop is followed directly by the
`    sweeping = learned("Sweeping Strikes") ...` block (with one blank line between).

How to patch it safely: (a) one `*** Update File` patch that inserts the two blocks before the `names = ...` line;
run the test file. (b) a second patch that deletes the two old copies (they now appear twice; the old copies are
the ones after the `for spell in plan:` loop). Run the test file again, then the fast suite.

Nothing else changes.

## Done when
- `tests/test_rage_priority.py` and `tests/test_warrior_aoe.py` pass; no other new failures apart from warrior pins.
