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
    dungeons = {m["ID"]: m for m in maps if m.get("InstanceType") == DUNGEON}
    tuning_by_id = {t["ID"]: t for t in tunings}
    result: dict[str, int] = {}
    for difficulty in difficulties:
        if difficulty.get("DifficultyID") != NORMAL:
            continue
        dungeon = dungeons.get(difficulty.get("MapID", ""))
        if dungeon is None:
            continue
        tuning_id = difficulty.get("ContentTuningID")
        if tuning_id in (None, "0"):
            continue
        tuning = tuning_by_id.get(tuning_id)
        if tuning is None:
            continue
        result[dungeon["MapName_lang"]] = int(tuning["MinLevelSquish"])
    return dict(sorted(result.items(), key=lambda item: (item[1], item[0])))
