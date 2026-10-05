# Task #152 (priest): classify every priest talent

Make the `priest` cases of `tests/test_opponent_classes.py` pass. Edit only `src/wowforever/classes/priest.py`. Do not edit the tests or fixtures.

## Why
The priest's Forever talent trees and spells already load: `LAYOUT`, `SKILL_LINES`, the registry entry and trimmed fixtures are in place. Nothing about the priest is modeled yet (it is a PvP opponent, #34), so every talent goes into `UNMODELED` with a one-line reason, the same way `src/wowforever/classes/warrior.py` does. Read that file first and copy its shape.

## What to write
Fill `UNMODELED` in `src/wowforever/classes/priest.py` with every priest talent. Each value is either:
- `"grants_spell"` for a talent that teaches an activated ability or spell. The test requires these (see `CLASSES["priest"]` in the test): any talent whose text reads like an ability ("Instantly…", "When activated…", "Summons…", "Heals the target…", "Deals … damage", a form) is `grants_spell` too.
- `"<category>: <what it does, a few words>"` with one of: `damage`, `healing`, `resource` (mana, rage, energy), `defensive`, `control` (stuns, roots, fears, slows, interrupts, silences), `mobility`, `threat`, `pet`, `buff` (auras, blessings, totems, curses on allies/enemies that aren't control), `form` (shapeshift forms), `utility`, `proc`.

Get every talent's tree, name and rank text with this command (run it as is):

    .venv/Scripts/python tools/list_talents.py priest

Pick the category from what the talent mostly does. Keep the dict in tree order with a comment line before each tree. Leave `TALENT_EFFECTS` empty and remove the TODO comment.

## Environment note
The package is already installed in `.venv` (editable). Before you start, the `priest` cases fail twice: coverage (talents in neither dict) and the `grants_spell` check. Other classes' cases fail too; ignore them. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Write the whole dict in one patch. Iterate with:

    .venv/Scripts/python -m pytest tests/test_opponent_classes.py -k priest

## Done when
`.venv/Scripts/python -m pytest tests/test_opponent_classes.py -k priest` passes.
