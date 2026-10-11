"""Forever Logs statistics refresh (#172): URLs, cache names, key handling. Offline: a fake `get` stands in for HTTP."""

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from wowforever.sources.foreverlogs_api import (
    BASE, VARIANTS, cache_name, fetch_statistics, read_api_key, statistics_url,
)

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
