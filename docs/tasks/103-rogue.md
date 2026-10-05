# Task #103 (part 2): classify every rogue talent

Make `tests/test_rogue.py` pass without breaking the rest of the suite. Edit only `src/wowforever/classes/rogue.py`. Do not edit the tests or fixtures.

## Why
The rogue's Forever talent trees and spells already load: `LAYOUT`, `SKILL_LINES`, the registry entry and trimmed fixtures are in place. Melee damage isn't modeled until #111, so for now every talent goes into `UNMODELED` with a one-line reason, the same way `classes/mage.py` lists its unmodeled talents.

## What to write
Fill `UNMODELED` in `src/wowforever/classes/rogue.py` with all 53 rogue talents. Each value is either:
- `"grants_spell"` for a talent that teaches an activated ability (Mutilate, Adrenaline Rush, Blade Flurry, Preparation, Premeditation, Hemorrhage, Cold Blood, Ghostly Strike, Riposte, and any other whose rank text reads like an ability: "Instantly attacks…", "When activated…", "A strike that…"), or
- `"<category>: <what it does, a few words>"`, with one of these categories:
  - `melee damage`: more weapon or ability damage, crit, hit, or attack speed. End the reason with `(#111)`, e.g. `"melee damage: Sinister Strike/Backstab crit (#111)"`.
  - `resource`: energy or combo points (Relentless Strikes, Ruthlessness, Setup, Thousand Cuts…).
  - `defensive`: dodge, parry, damage taken, Evasion/Feint.
  - `control`: stuns, Gouge, Blind, Kick, Kidney Shot, Sap, disarm.
  - `stealth`: Stealth, Vanish, Ambush/Garrote openers, Camouflage, Master of Deception.
  - `mobility`: Sprint and movement.
  - `utility`: range, threat, traps, Distract, cooldown resets that fit nothing else.
  - `poison`: poison damage or proc chance.
  - `proc`: a chance-based effect that fits nothing else.

To see every talent's name and rank text, run this from the repo root:
```
.venv/Scripts/python -c "from pathlib import Path; from wowforever.classes import class_module; from wowforever.normalize import normalize_class, read_tables; from wowforever.sources.wowforevertalent import parse_page; R=class_module('rogue'); F=Path('tests/fixtures'); c,_=normalize_class(read_tables(F/'wago-1.60.1.70205-rogue'), R.LAYOUT, parse_page((F/'wowforevertalent'/'rogue.html').read_text(encoding='utf-8')), wago_build='x'); [print(t.name, '|', t.rank_text[-1][:160].replace(chr(10), ' ')) for t in c.talents]"
```

Pick the category from what the talent mostly does. Keep the dict in tree order (Assassination, Combat, Subtlety), with a comment line before each tree. Leave `TALENT_EFFECTS` empty and remove the TODO comment.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_rogue.py` has 2 expected failures: coverage (talents in neither dict) and the `grants_spell` check. Fixing those is the task. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Iterate with `.venv/Scripts/python -m pytest tests/test_rogue.py`, then run the full suite once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
