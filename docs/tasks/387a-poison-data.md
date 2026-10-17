# Task #387 (part 1): the poisons' damage spells in the rogue's spell list

Make `tests/test_poison_data.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order. Step 4 runs a tool that rewrites `data/datasets/1.60.1.70425.json`; run it
  exactly once, after steps 1-3.
- Before you start, all 3 tests in `tests/test_poison_data.py` fail.

## Why
Rogue poisons deal no damage in the model: the poison damage spells (Instant Poison 8680 ..., Deadly Poison 2818
...) aren't on a rogue skill line, so `class_spells` never reads them. A class can now name extra spell ids, with
the name their ranks share.

## Step 1: `src/wowforever/normalize_spells.py`, `class_spells`
1. The signature becomes
   `def class_spells(tables: Tables, *, skill_lines: Sequence[int], extra_spells: Mapping[int, str] = {}) -> tuple[SpellRank, ...]:`
   (import `Mapping` from `collections.abc` next to `Sequence` if it isn't imported yet).
2. Docstring: `"""Every trainable spell rank of the class, sorted by (name, rank); `extra_spells` adds spells by id under
   a shared name (rogue poisons, #387)."""`
3. Directly before the line `    trainable.sort()`, add:
   ```python
       for spell_id, name in extra_spells.items():
           level_row = levels.get(spell_id)
           if spell_id not in seen and level_row is not None and int(_f(level_row["BaseLevel"])) > 0:
               seen.add(spell_id)
               trainable.append((name, int(_f(level_row["BaseLevel"])), spell_id))
   ```

## Step 2: `src/wowforever/classes/rogue.py`
After the line `SKILL_LINES = (253, 38, 39, 40)` add a blank line and:
```python
# Poison damage spells (#387), not on a skill line: each rank's proc spell, by learn level.
EXTRA_SPELLS = {
    8680: "Instant Poison", 8685: "Instant Poison", 8689: "Instant Poison", 11335: "Instant Poison",
    11336: "Instant Poison", 11337: "Instant Poison",
    2818: "Deadly Poison", 2819: "Deadly Poison", 11353: "Deadly Poison", 11354: "Deadly Poison",
    25349: "Deadly Poison",
}
```

## Step 3: `src/wowforever/update.py`
The line
`        cls, spells=normalize_spells_module.class_spells(tables, skill_lines=module.SKILL_LINES)`
becomes
```python
        cls, spells=normalize_spells_module.class_spells(tables, skill_lines=module.SKILL_LINES,
                                                         extra_spells=getattr(module, "EXTRA_SPELLS", {}))
```

## Step 4: `tools/add_extra_spells.py` (new), then run it
Create it with exactly this content:
```python
"""Add classes' EXTRA_SPELLS (#387) to saved datasets from the cached client tables.

    .venv/Scripts/python tools/add_extra_spells.py <build> [<build> ...]

Reads data/cache/wago/<build>/, runs normalize_spells.class_spells with the class's EXTRA_SPELLS, and appends
the spells the saved dataset doesn't have yet to data/datasets/<build>.json (sorted by name, rank), printing
each. Everything else in the dataset stays as saved.
"""

import dataclasses
import json
import sys
from pathlib import Path

from wowforever.classes import class_module
from wowforever.normalize import read_tables
from wowforever.normalize_spells import class_spells

ROOT = Path(__file__).resolve().parents[1]

for build in sys.argv[1:]:
    tables = read_tables(ROOT / "data" / "cache" / "wago" / build)
    path = ROOT / "data" / "datasets" / f"{build}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    added = 0
    for c in data["classes"]:
        module = class_module(c["class_name"])
        extra = getattr(module, "EXTRA_SPELLS", {})
        if not extra:
            continue
        have = {s["spell_id"] for s in c["spells"]}
        for spell in class_spells(tables, skill_lines=module.SKILL_LINES, extra_spells=extra):
            if spell.spell_id in extra and spell.spell_id not in have:
                c["spells"].append(dataclasses.asdict(spell))
                print(f"{build} {c['class_name']} {spell.name} r{spell.rank} (spell {spell.spell_id})")
                added += 1
        c["spells"].sort(key=lambda s: (s["name"], s["rank"]))
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"{build}: {added} spells added")
```
Then run `.venv/Scripts/python tools/add_extra_spells.py 1.60.1.70425` once. It prints 11 spells added.

Nothing else changes.

## Done when
- `tests/test_poison_data.py` passes (3 tests); `git diff --stat data/datasets` shows only the 70425 dataset,
  with additions only; the fast suite has no new failures.
