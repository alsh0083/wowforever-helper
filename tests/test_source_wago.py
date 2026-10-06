"""Tests for the wago.tools fetcher (#6). Fixtures: build list and talent tables saved 2026-10-04."""

import hashlib
import json
from pathlib import Path

from wowforever.sources.wago import TABLES, fetch_build, forever_builds, latest_build, table_url

FIXTURES = Path(__file__).parent / "fixtures" / "wago"
BUILDS = json.loads((FIXTURES / "builds.json").read_text(encoding="utf-8"))


def test_forever_builds_are_unique_and_numerically_sorted():
    builds = forever_builds(BUILDS)
    assert builds[0] == "1.60.1.69876"
    assert builds[-1] == "1.60.1.70205"
    assert len(builds) == len(set(builds))
    assert all(b.startswith("1.60.") for b in builds)
    assert latest_build(BUILDS) == "1.60.1.70205"


def test_table_url():
    assert table_url("Talent", "1.60.1.70205") == "https://wago.tools/db2/Talent/csv?build=1.60.1.70205"


def test_required_tables_present():
    for name in ("Talent", "TalentTab", "SpellName", "SpellEffect", "SpellMisc", "SpellLevels",
                 "SpellCastTimes", "SpellPower", "SpellDuration", "SpellRange", "SpellCooldowns",
                 "SpellTargetRestrictions", "SkillLineAbility", "SpellClassOptions", "Spell"):
        assert name in TABLES


def fake_http(calls):
    def http_get(url):
        calls.append(url)
        table = url.split("/db2/")[1].split("/")[0]
        return f"ID,Name\n1,{table}\n"
    return http_get


def test_fetch_build_writes_cache_and_manifest(tmp_path):
    calls = []
    cache, raw = tmp_path / "cache", tmp_path / "raw"
    manifest_path = fetch_build("1.60.1.70205", http_get=fake_http(calls), cache_dir=cache,
                                manifest_dir=raw, tables=("Talent", "TalentTab"), delay=0)
    assert manifest_path == raw / "1.60.1.70205" / "manifest.json"
    assert len(calls) == 2
    body = (cache / "1.60.1.70205" / "Talent.csv").read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["build"] == "1.60.1.70205"
    assert manifest["source"] == "wago.tools"
    entry = manifest["files"]["Talent"]
    assert entry["sha256"] == hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert entry["url"] == table_url("Talent", "1.60.1.70205")
    assert "fetched_at" in manifest


def test_fetch_build_is_a_noop_when_manifest_and_cache_complete(tmp_path):
    cache, raw = tmp_path / "cache", tmp_path / "raw"
    fetch_build("1.60.1.70205", http_get=fake_http([]), cache_dir=cache, manifest_dir=raw,
                tables=("Talent",), delay=0)
    calls = []
    fetch_build("1.60.1.70205", http_get=fake_http(calls), cache_dir=cache, manifest_dir=raw,
                tables=("Talent",), delay=0)
    assert calls == []


def test_fetch_build_refetches_missing_cache_and_verifies_hash(tmp_path):
    cache, raw = tmp_path / "cache", tmp_path / "raw"
    fetch_build("1.60.1.70205", http_get=fake_http([]), cache_dir=cache, manifest_dir=raw,
                tables=("Talent",), delay=0)
    (cache / "1.60.1.70205" / "Talent.csv").unlink()           # cache is disposable
    calls = []
    fetch_build("1.60.1.70205", http_get=fake_http(calls), cache_dir=cache, manifest_dir=raw,
                tables=("Talent",), delay=0)
    assert len(calls) == 1
    assert (cache / "1.60.1.70205" / "Talent.csv").exists()


def test_without_a_downloader_tables_come_from_the_cache(tmp_path):
    # wago.tools' table CSVs aren't in its published API: nothing is fetched by default
    import pytest

    from wowforever.sources.wago import MissingTables

    cache, raw = tmp_path / "cache", tmp_path / "raw"
    with pytest.raises(MissingTables) as missing:
        fetch_build("1.60.1.70205", cache_dir=cache, manifest_dir=raw, tables=("Talent", "SpellName"))
    assert missing.value.tables == ["Talent", "SpellName"] and "csv?build=1.60.1.70205" in str(missing.value)
    for table in ("Talent", "SpellName"):                         # saved from the browser
        (cache / "1.60.1.70205" / f"{table}.csv").write_text(f"ID\n{table}\n", encoding="utf-8")
    manifest = json.loads(fetch_build("1.60.1.70205", cache_dir=cache, manifest_dir=raw,
                                      tables=("Talent", "SpellName")).read_text(encoding="utf-8"))
    assert manifest["files"]["Talent"]["saved_by"] == "browser"
