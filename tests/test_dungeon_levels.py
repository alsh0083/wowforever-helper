"""Dungeon level floors from the client's ContentTuning (#258)."""

from wowforever.dungeon_levels import floors

MAPS = [
    {"ID": "33", "MapName_lang": "Shadowfang Keep", "InstanceType": "1"},
    {"ID": "34", "MapName_lang": "Stormwind Stockade", "InstanceType": "1"},
    {"ID": "409", "MapName_lang": "Molten Core", "InstanceType": "2"},        # raid
    {"ID": "0", "MapName_lang": "Eastern Kingdoms", "InstanceType": "0"},     # world
    {"ID": "2950", "MapName_lang": "Excavation Site: Wetlands", "InstanceType": "1"},
]
DIFFICULTIES = [
    {"MapID": "33", "DifficultyID": "1", "ContentTuningID": "5249"},
    {"MapID": "33", "DifficultyID": "201", "ContentTuningID": "0"},           # other difficulty
    {"MapID": "34", "DifficultyID": "1", "ContentTuningID": "5250"},
    {"MapID": "409", "DifficultyID": "9", "ContentTuningID": "5300"},
    {"MapID": "2950", "DifficultyID": "1", "ContentTuningID": "0"},           # no tuning row
    {"MapID": "999", "DifficultyID": "1", "ContentTuningID": "5249"},         # map not in Map
]
TUNINGS = [
    {"ID": "5249", "MinLevelSquish": "18", "MaxLevelSquish": "18"},
    {"ID": "5250", "MinLevelSquish": "23", "MaxLevelSquish": "23"},
    {"ID": "5300", "MinLevelSquish": "60", "MaxLevelSquish": "60"},
]


def test_normal_difficulty_dungeons_get_their_tuning_floor():
    assert floors(MAPS, DIFFICULTIES, TUNINGS) == {"Shadowfang Keep": 18, "Stormwind Stockade": 23}


def test_a_tuning_id_missing_from_the_tuning_table_is_skipped():
    assert floors(MAPS, DIFFICULTIES, TUNINGS[1:]) == {"Stormwind Stockade": 23}


def test_result_is_sorted_by_floor_then_name():
    rows = MAPS + [{"ID": "48", "MapName_lang": "Blackfathom Deeps", "InstanceType": "1"}]
    diffs = DIFFICULTIES + [{"MapID": "48", "DifficultyID": "1", "ContentTuningID": "5249"}]
    assert list(floors(rows, diffs, TUNINGS)) == ["Blackfathom Deeps", "Shadowfang Keep", "Stormwind Stockade"]
