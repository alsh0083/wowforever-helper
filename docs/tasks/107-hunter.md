# Task #107: classify every hunter talent

Make `tests/test_hunter.py` pass without breaking the rest of the suite. Edit only `src/wowforever/classes/hunter.py`. Do not edit the tests or fixtures.

## Why
The hunter's Forever talent trees and spells already load: `LAYOUT`, `SKILL_LINES`, the registry entry and trimmed fixtures are in place. Ranged, melee and pet damage aren't modeled until #111, so for now every talent goes into `UNMODELED` with a one-line reason, the same way `classes/mage.py` lists its unmodeled talents.

## What to write
Fill `UNMODELED` in `src/wowforever/classes/hunter.py` with all 50 hunter talents. Each value is either:
- `"grants_spell"` for a talent that teaches an activated ability (Bestial Wrath, Intimidation, Trueshot Aura, Sniper Shot, Strider Kick, Scatter Shot, Deterrence, Counterattack, Summon Hawk, and any other whose rank text reads like an ability: "When activated…", "A shot that…", "Summons…"), or
- `"<category>: <what it does, a few words>"`, with one of these categories:
  - `ranged damage`: shot damage, crit, hit, ranged attack speed or attack power. End with `(#111)`.
  - `melee damage`: Raptor Strike, Mongoose Bite, melee crit or speed. End with `(#111)`.
  - `pet`: pet damage, health or abilities. End with `(#111)`. Note in the reason if a talent is meant for playing without a pet (e.g. Lone Wolf).
  - `resource`: mana cost or regeneration (Efficiency, Rapid Recuperation…).
  - `defensive`: dodge, parry, health, armor, damage taken.
  - `control`: Concussive Shot, Wing Clip, Scatter Shot, roots, stuns, slows.
  - `trap`: trap effects and cooldowns (Clever Traps, Entrapment, Resourcefulness…).
  - `mobility`: movement speed, Disengage, snare reduction.
  - `utility`: range, tracking, threat, aspects, anything that fits nothing else.
  - `proc`: a chance-based effect that fits nothing else.

To see every talent's name and rank text, run this from the repo root:
```
.venv/Scripts/python -c "from pathlib import Path; from wowforever.classes import class_module; from wowforever.normalize import normalize_class, read_tables; from wowforever.sources.wowforevertalent import parse_page; R=class_module('hunter'); F=Path('tests/fixtures'); c,_=normalize_class(read_tables(F/'wago-1.60.1.70205-hunter'), R.LAYOUT, parse_page((F/'wowforevertalent'/'hunter.html').read_text(encoding='utf-8')), wago_build='x'); [print(t.name, '|', t.rank_text[-1][:160].replace(chr(10), ' ')) for t in c.talents]"
```

Pick the category from what the talent mostly does. Keep the dict in tree order (Beast Mastery, Marksmanship, Survival), with a comment line before each tree. Leave `TALENT_EFFECTS` empty and remove the TODO comment.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_hunter.py` has 2 expected failures: coverage (talents in neither dict) and the `grants_spell` check. Fixing those is the task. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Iterate with `.venv/Scripts/python -m pytest tests/test_hunter.py`, then run the full suite once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
