"""Forever Logs statistics refresh (#172): URLs, cache names, key handling. Offline: a fake `get` stands in for HTTP."""

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from wowforever.sources.foreverlogs_api import (
    BASE, PER_BOSS, VARIANTS, boss_statistics_url, cache_name, fetch_boss_statistics, fetch_statistics,
    read_api_key, read_boss_list, statistics_url,
)

ROOT = Path(__file__).resolve().parents[1]

OK = json.dumps({"success": True, "phase": 1, "statistics": {}})


def test_cache_names_match_the_files_already_cached():
    assert cache_name("Blackfathom Deeps") == "Blackfathom_Deeps"
    assert cache_name("Excavation Site: Wetlands") == "Excavation_Site__Wetlands"
    assert cache_name("Onyxia's Lair") == "Onyxia_s_Lair"
    assert cache_name("Dire Maul - East") == "Dire_Maul_-_East"
    assert cache_name("Zul'Farrak") == "Zul_Farrak"


def test_variants_are_the_four_cached_statistic_sets():
    assert VARIANTS == {
        "stats": {"metric": "avg_dps", "role": "dps"},
        "stats-boss-only": {"metric": "avg_dps", "role": "dps", "damageMode": "boss-only"},
        "stats-hps": {"metric": "avg_hps"},
        "stats-role-tank": {"metric": "avg_dps", "role": "tank"},
    }


def test_statistics_url_asks_for_phase_1_all_difficulties_and_the_location():
    url = statistics_url("Onyxia's Lair", VARIANTS["stats-boss-only"])
    parts = urlsplit(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == BASE + "/statistics"
    assert {k: v[0] for k, v in parse_qs(parts.query).items()} == {
        "phase": "1", "difficulty": "all", "metric": "avg_dps", "role": "dps",
        "damageMode": "boss-only", "location": "Onyxia's Lair"}
    assert "key" not in parts.query.lower()                # keys never go in the query string


def test_fetch_writes_each_response_under_its_variant_and_sends_the_key_as_a_header(tmp_path):
    calls, sleeps = [], []

    def get(url, headers):
        calls.append((url, headers))
        return OK

    written = fetch_statistics(tmp_path, "secret-key", variants=["stats", "stats-hps"],
                               locations=["Deadmines", "Onyxia's Lair"], get=get,
                               sleep=sleeps.append, delay=2.0)
    assert written == [tmp_path / "stats" / "Deadmines.json", tmp_path / "stats" / "Onyxia_s_Lair.json",
                       tmp_path / "stats-hps" / "Deadmines.json", tmp_path / "stats-hps" / "Onyxia_s_Lair.json"]
    assert all(path.read_text(encoding="utf-8") == OK for path in written)
    assert len(calls) == 4 and all(h == {"Authorization": "Bearer secret-key"} for _, h in calls)
    assert sleeps == [2.0, 2.0, 2.0]                         # between requests, not before the first
    assert not any("secret-key" in p.read_text(encoding="utf-8") for p in written)


def test_an_unsuccessful_response_raises_and_names_the_location(tmp_path):
    def get(url, headers):
        return json.dumps({"success": False, "error": "rate limited"})

    with pytest.raises(ValueError, match="Deadmines"):
        fetch_statistics(tmp_path, "k", variants=["stats"], locations=["Deadmines"], get=get,
                         sleep=lambda s: None)
    assert not (tmp_path / "stats" / "Deadmines.json").exists()


def test_unknown_variant_is_rejected_before_any_request(tmp_path):
    def get(url, headers):
        raise AssertionError("no request expected")

    with pytest.raises(ValueError, match="stats-nope"):
        fetch_statistics(tmp_path, "k", variants=["stats-nope"], locations=["Deadmines"], get=get,
                         sleep=lambda s: None)


def test_api_key_comes_from_the_environment_first_then_dotenv(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text('OTHER=1\nFOREVERLOGS_API_KEY="from-file"\n', encoding="utf-8")
    assert read_api_key({"FOREVERLOGS_API_KEY": "from-env"}, dotenv) == "from-env"
    assert read_api_key({}, dotenv) == "from-file"
    with pytest.raises(ValueError, match="FOREVERLOGS_API_KEY"):
        read_api_key({}, tmp_path / "missing.env")


def test_boss_statistics_url_asks_for_one_boss_boss_only_dps():
    parts = urlsplit(boss_statistics_url("Molten Core", 12118))
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == BASE + "/statistics"
    assert {k: v[0] for k, v in parse_qs(parts.query).items()} == {
        "phase": "1", "difficulty": "all", "metric": "avg_dps", "role": "dps",
        "damageMode": "boss-only", "location": "Molten Core", "bossId": "12118"}


def test_per_boss_is_not_a_default_variant():
    assert PER_BOSS == "stats-per-boss"
    assert PER_BOSS not in VARIANTS                          # a plain refresh never spends the per-boss requests


def test_fetch_boss_statistics_writes_one_file_per_boss_id(tmp_path):
    calls, sleeps = [], []

    def get(url, headers):
        calls.append((url, headers))
        return OK

    written = fetch_boss_statistics(tmp_path, "secret-key", bosses=[("Molten Core", 12118), ("Molten Core", 11982)],
                                    get=get, sleep=sleeps.append, delay=2.0)
    assert written == [tmp_path / "stats-per-boss" / "12118.json", tmp_path / "stats-per-boss" / "11982.json"]
    assert all(path.read_text(encoding="utf-8") == OK for path in written)
    assert [url for url, _ in calls] == [boss_statistics_url("Molten Core", 12118),
                                         boss_statistics_url("Molten Core", 11982)]
    assert all(h == {"Authorization": "Bearer secret-key"} for _, h in calls)
    assert sleeps == [2.0]


def test_an_unsuccessful_boss_response_raises_and_names_the_boss(tmp_path):
    def get(url, headers):
        return json.dumps({"success": False, "error": "rate limited"})

    with pytest.raises(ValueError, match="12118"):
        fetch_boss_statistics(tmp_path, "k", bosses=[("Molten Core", 12118)], get=get, sleep=lambda s: None)
    assert not (tmp_path / "stats-per-boss" / "12118.json").exists()


def test_boss_list_reads_location_and_boss_id_in_file_order(tmp_path):
    path = tmp_path / "bosses.toml"
    path.write_text('''bosses = [
  { id = 12118, name = "Lucifron", location = "Molten Core" },
  { id = 639, name = "Edwin VanCleef", location = "Deadmines" },
]
''', encoding="utf-8")
    assert read_boss_list(path) == [("Molten Core", 12118), ("Deadmines", 639)]
    path.write_text("bosses = []\n", encoding="utf-8")
    assert read_boss_list(path) == []


def test_the_shipped_boss_list_parses():
    bosses = read_boss_list(ROOT / "config" / "single_target_bosses.toml")
    assert all(isinstance(loc, str) and isinstance(boss, int) for loc, boss in bosses)
