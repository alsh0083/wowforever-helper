"""Forever Logs by week and day (#381): post-patch slices of the statistics, a 429 back-off, and validate-logs
reading several slice folders. Offline: a fake `get` stands in for HTTP."""

import io
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from wowforever.sources.foreverlogs_api import (RETRY_SECONDS, VARIANTS, fetch_statistics, slice_folder,
                                                statistics_url)
from wowforever.validate import log_averages, log_percentiles

OK = json.dumps({"success": True, "phase": 1, "statistics": {}})


def query(url):
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


def test_statistics_url_takes_week_and_day():
    assert "weekNumber" not in query(statistics_url("Deadmines", VARIANTS["stats"]))
    q = query(statistics_url("Deadmines", VARIANTS["stats"], week=146))
    assert q["weekNumber"] == "146" and "dayNumber" not in q
    q = query(statistics_url("Deadmines", VARIANTS["stats"], week=147, day=3))
    assert (q["weekNumber"], q["dayNumber"], q["location"]) == ("147", "3", "Deadmines")


def test_slice_folder_names():
    assert slice_folder("stats", None, None) == "stats"
    assert slice_folder("stats", 146, None) == "stats-w146"
    assert slice_folder("stats-boss-only", 147, 2) == "stats-boss-only-w147-d2"


def test_fetch_writes_one_folder_per_slice(tmp_path):
    calls = []

    def get(url, headers):
        calls.append(url)
        return OK

    written = fetch_statistics(tmp_path, "k", variants=["stats"], locations=["Deadmines"], get=get,
                               sleep=lambda s: None, slices=[(146, None), (147, 2)])
    assert written == [tmp_path / "stats-w146" / "Deadmines.json", tmp_path / "stats-w147-d2" / "Deadmines.json"]
    assert [query(u).get("weekNumber") for u in calls] == ["146", "147"]
    assert query(calls[1])["dayNumber"] == "2"


def test_default_fetch_is_unchanged(tmp_path):
    written = fetch_statistics(tmp_path, "k", variants=["stats"], locations=["Deadmines"], get=lambda u, h: OK,
                               sleep=lambda s: None)
    assert written == [tmp_path / "stats" / "Deadmines.json"]


def rate_limited(url):
    return HTTPError(url, 429, "Too Many Requests", {}, io.BytesIO(b""))


def test_429_backs_off_once_then_retries(tmp_path):
    sleeps, answers = [], [rate_limited, OK]

    def get(url, headers):
        a = answers.pop(0)
        if a is rate_limited:
            raise a(url)
        return a

    written = fetch_statistics(tmp_path, "k", variants=["stats"], locations=["Deadmines"], get=get,
                               sleep=sleeps.append)
    assert written == [tmp_path / "stats" / "Deadmines.json"] and sleeps == [RETRY_SECONDS]


def test_a_second_429_raises(tmp_path):
    def get(url, headers):
        raise rate_limited(url)

    with pytest.raises(HTTPError):
        fetch_statistics(tmp_path, "k", variants=["stats"], locations=["Deadmines"], get=get, sleep=lambda s: None)


def test_log_averages_add_up_over_slice_folders(tmp_path):
    levels = tmp_path / "levels.toml"
    levels.write_text('"Deadmines" = 20\n', encoding="utf-8")
    dirs = []
    for name, avg, n, p75 in (("stats-w146", 40.0, 2, 50.0), ("stats-w147", 70.0, 1, 80.0)):
        d = tmp_path / name
        d.mkdir()
        (d / "Deadmines.json").write_text(json.dumps({"location": "Deadmines", "statistics": {
            "Rogue": {"specs": {"Combat": {"avg": avg, "total_parses": n, "percentiles": {"p75": p75}}}}}}),
            encoding="utf-8")
        dirs.append(d)
    # (40 x 2 + 70 x 1) / 3 = 50; p75 (50 x 2 + 80 x 1) / 3 = 60
    assert log_averages(dirs, levels) == {("rogue", "Combat", 20): (50.0, 3)}
    assert log_percentiles(dirs, levels)[("rogue", "Combat", 20)]["p75"] == pytest.approx(60.0)
    assert log_averages(dirs[0], levels) == {("rogue", "Combat", 20): (40.0, 2)}
