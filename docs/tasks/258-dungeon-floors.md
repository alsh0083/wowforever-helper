# Task #258: dungeon level floors from ContentTuning rows

Make `tests/test_dungeon_levels.py` pass. Do not edit the tests. Create one file: `src/wowforever/dungeon_levels.py`.

## Why
The client's `ContentTuning` table holds each dungeon's minimum level, linked from `MapDifficulty.ContentTuningID`. A pure function turns the three tables' CSV rows into dungeon name → floor.

## Change
Create `src/wowforever/dungeon_levels.py`:

```python
"""Dungeon level floors from the client's ContentTuning (#258).

MapDifficulty.ContentTuningID -> ContentTuning.MinLevelSquish gives each dungeon's minimum level in
Forever's own client data (it matches Forever's published ranges: Hall of Thanes 13, City of Dalaran 28).
Rows are CSV dicts of the Map, MapDifficulty and ContentTuning tables (wago.tools column names).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

DUNGEON = "1"          # Map.InstanceType
NORMAL = "1"           # MapDifficulty.DifficultyID


def floors(maps: Iterable[Mapping[str, str]], difficulties: Iterable[Mapping[str, str]],
           tunings: Iterable[Mapping[str, str]]) -> dict[str, int]:
    """Dungeon name -> minimum level, sorted by level then name."""
```

Body rules:
- Index `maps` by `ID` (keep only rows whose `InstanceType` is `DUNGEON`) and `tunings` by `ID`.
- For each `difficulties` row with `DifficultyID == NORMAL`, look up its map (skip if missing or not a dungeon) and its tuning by `ContentTuningID` (skip if `"0"` or missing). Record `MapName_lang` → `int(MinLevelSquish)`.
- Return a new dict sorted by `(level, name)`.

Standard library only. Change no other file.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_dungeon_levels.py` fails with `ModuleNotFoundError: No module named 'wowforever.dungeon_levels'`. That's the expected failure. Install nothing and ask for no elevation. Write the file with `tools/apply_patch.py` (`*** Add File:`; see AGENTS.md).

## Done when
`.venv/Scripts/python -m pytest tests/test_dungeon_levels.py` passes.
