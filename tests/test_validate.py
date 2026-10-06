"""Model vs Forever Logs comparison (#172)."""

import json

from wowforever.validate import compare, log_averages, markdown, model_scores


def test_log_averages_bucket_by_dungeon_level(tmp_path):
    levels = tmp_path / "levels.toml"
    levels.write_text('"Deadmines" = 20\n"Razorfen Kraul" = 30\n', encoding="utf-8")
    stats = tmp_path / "stats"
    stats.mkdir()
    for name, avg, n in (("Deadmines", 40.0, 2), ("Razorfen Kraul", 70.0, 1)):
        (stats / f"{name}.json").write_text(json.dumps({"location": name, "statistics": {
            "Rogue": {"specs": {"Combat": {"avg": avg, "total_parses": n}}}}}), encoding="utf-8")
    (stats / "empty.json").write_text(json.dumps({"location": "Molten Core", "statistics": {}}), encoding="utf-8")
    assert log_averages(stats, levels) == {("rogue", "Combat", 20): (40.0, 2), ("rogue", "Combat", 30): (70.0, 1)}


def test_compare_maps_specs_to_builds_by_main_tree():
    report = {"class": "rogue", "talents": {"1": {"tree": "Combat"}, "2": {"tree": "Subtlety"}},
              "builds": [{"order": [1, 1, 2], "scores": {"dungeon": {"20": {"score": 50.0}, "30": {"score": 60.0}}}},
                         {"order": [2], "scores": {}}]}
    assert model_scores(report) == {("Combat", 20): [50.0], ("Combat", 30): [60.0]}
    rows = compare([report], {("rogue", "Combat", 20): (40.0, 2), ("rogue", "Subtlety", 20): (30.0, 1)})
    assert rows == [{"class": "rogue", "spec": "Combat", "level": 20, "log_dps": 40.0, "parses": 2,
                     "model_min": 50.0, "model_max": 50.0, "ratio": 1.25}]
    assert "| Rogue | Combat | 20 | 40 (2) | 50 | 1.25 |" in markdown(rows)
