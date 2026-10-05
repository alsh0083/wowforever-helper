"""Tests for the wowforevertalent.com fetcher (#7). Fixture: mage page saved 2026-10-04."""

from pathlib import Path

import pytest

from wowforever.sources.wowforevertalent import (
    SnapshotConflict, decode_astro, fetch, parse_page, snapshot,
)

FIXTURE = Path(__file__).parent / "fixtures" / "wowforevertalent" / "mage.html"
HTML = FIXTURE.read_text(encoding="utf-8")


def test_decode_astro_encoding():
    assert decode_astro([0]) is None                                  # undefined
    assert decode_astro([0, 5]) == 5
    assert decode_astro([0, "x"]) == "x"
    assert decode_astro([1, [[0, 1], [0, 2]]]) == [1, 2]
    assert decode_astro([0, {"a": [0, 1], "b": [1, [[0, "z"]]]}]) == {"a": 1, "b": ["z"]}
    with pytest.raises(ValueError):
        decode_astro([9, "unsupported tag"])


def test_parse_page_versions():
    page = parse_page(HTML)
    assert page.class_id == "mage"
    assert page.game_build == "1.60.1.70170"
    assert page.page_data_version == "beta-20261003-adadac42"   # <... data-version="...">
    assert page.props_version == "beta-20261002-f8438f7e"       # calculator props "version"


def test_parse_page_trees_and_talents():
    page = parse_page(HTML)
    assert [t["name"] for t in page.trees] == ["Arcane", "Fire", "Frost"]
    fire = page.trees[1]
    assert len(fire["talents"]) == 17
    ignite = next(t for t in fire["talents"] if t["name"] == "Ignite")
    assert (ignite["id"], ignite["row"], ignite["col"], ignite["maxRank"]) == ("1-2-1", 2, 1, 5)
    assert "40%" in ignite["ranks"][4]["text"]
    assert ignite["classic"]["status"] == "same"
    assert ignite["prerequisite"] is None


def test_parse_page_prerequisites_changes_and_removed():
    arcane, _, frost = parse_page(HTML).trees
    arcane_power = next(t for t in arcane["talents"] if t["name"] == "Arcane Power")
    assert arcane_power["prerequisite"] == "0-5-2"
    ice_lance = next(t for t in frost["talents"] if t["name"] == "Ice Lance")
    assert ice_lance["classic"]["status"] == "new"
    assert [r["name"] for r in arcane["removed"]] == ["Magic Attunement"]


def test_snapshot_writes_html_and_manifest_once(tmp_path):
    path = snapshot(HTML, tmp_path, url="https://wowforevertalent.com/mage/")
    assert path == tmp_path / "beta-20261003-adadac42" / "mage.html"
    assert path.read_text(encoding="utf-8") == HTML
    manifest = (path.parent / "manifest.json").read_text(encoding="utf-8")
    assert '"sha256"' in manifest and '"game_build": "1.60.1.70170"' in manifest
    mtime = path.stat().st_mtime_ns
    assert snapshot(HTML, tmp_path, url="https://wowforevertalent.com/mage/") == path
    assert path.stat().st_mtime_ns == mtime                      # unchanged page: no rewrite


def test_snapshot_refuses_to_overwrite_different_content(tmp_path):
    snapshot(HTML, tmp_path, url="u")
    with pytest.raises(SnapshotConflict):
        snapshot(HTML.replace("Ignite", "Ignyte"), tmp_path, url="u")


def test_fetch_uses_injected_http_get(tmp_path):
    calls = []

    def http_get(url):
        calls.append(url)
        return HTML

    path = fetch("mage", http_get=http_get, raw_dir=tmp_path)
    assert calls == ["https://wowforevertalent.com/mage/"]
    assert path.exists()


def test_popular_builds_with_talent_names():
    from wowforever.sources.wowforevertalent import popular_builds
    page = parse_page(HTML)
    assert page.popular["counts"]["builds"] == 40615
    top = popular_builds(page)
    assert len(top) == 5
    first = top[0]
    assert first["points"] == [0, 29, 22] and first["saved"] == 172
    assert first["final"]["Heating Up"] == 1 and first["final"]["Fingers of Frost"] == 2
    assert sum(first["final"].values()) == 51
