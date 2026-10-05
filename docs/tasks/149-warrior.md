# Task #149: classify every warrior talent

Make `tests/test_warrior.py` pass without breaking the rest of the suite. Edit only `src/wowforever/classes/warrior.py`. Do not edit the tests or fixtures.

## Why
The warrior's Forever talent trees and spells already load: `LAYOUT`, `SKILL_LINES`, the registry entry and trimmed fixtures are in place. Nothing about the warrior is modeled yet (it will be a PvP opponent, #34), so every talent goes into `UNMODELED` with a one-line reason, the same way `classes/rogue.py` lists its talents.

## What to write
Fill `UNMODELED` in `src/wowforever/classes/warrior.py` with all 53 warrior talents. Each value is either:
- `"grants_spell"` for a talent that teaches an activated ability. These nine must be: Mortal Strike, Sweeping Strikes, Spearing Strike, Piercing Howl, Death Wish, Bloodthirst, Last Stand, Concussion Blow, Shield Slam.
- `"<category>: <what it does, a few words>"`, with one of these categories:
  - `melee damage`: more weapon or ability damage, crit, hit, attack speed, bleeds.
  - `rage`: Rage cost or Rage generation.
  - `defensive`: parry, block, dodge, health, damage taken, cooldowns of defensive abilities.
  - `control`: stuns, roots, slows, disarm, interrupts, fear.
  - `mobility`: Charge, Intercept and movement.
  - `threat`: threat generation.
  - `shout`: Battle Shout, Demoralizing Shout and other shouts.
  - `utility`: stance changes and anything that fits nothing else.
  - `proc`: a chance-based effect that fits nothing else.

Fifteen talents have no rank text, because wowforevertalent.com is a build behind the client (the list is `NO_RANK_TEXT` in the test). Classify those from the name alone, and end their reason with ` (no rank text)`, e.g. `"defensive: more Stamina (no rank text)"`. No other reason may end that way.

To see every talent's name and rank text, run this from the repo root:
```
.venv/Scripts/python -c "from pathlib import Path; from wowforever.classes import class_module; from wowforever.normalize import normalize_class, read_tables; from wowforever.sources.wowforevertalent import parse_page; W=class_module('warrior'); F=Path('tests/fixtures'); c,_=normalize_class(read_tables(F/'wago-1.60.1.70205-warrior'), W.LAYOUT, parse_page((F/'wowforevertalent'/'warrior.html').read_text(encoding='utf-8')), wago_build='x'); [print(t.name, '|', t.rank_text[-1][:160].replace(chr(10), ' ') if t.rank_text else '(no text)') for t in c.talents]"
```

Pick the category from what the talent mostly does. Keep the dict in tree order (Arms, Fury, Protection), with a comment line before each tree. Leave `TALENT_EFFECTS` empty and remove the TODO comment.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_warrior.py` has 2 expected failures: coverage (talents in neither dict) and the `grants_spell` check. Fixing those is the task. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Iterate with `.venv/Scripts/python -m pytest tests/test_warrior.py`. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest tests/test_warrior.py` passes.
