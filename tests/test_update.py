"""Tests for the on-demand update check (#13), against a fake HTTP server built from fixtures."""

import csv
import io
import json
from pathlib import Path

import pytest

from wowforever.update import check_for_updates

FIX = Path(__file__).parent / "fixtures"
BUILDS = json.loads((FIX / "wago" / "builds.json").read_text(encoding="utf-8"))
HTML = (FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")


def merged_tables():
    """Fixture CSVs by table name; SpellName exists in both fixture dirs, so union its rows."""
    tables = {}
    for d in ("wago-1.60.1.70205", "wago-1.60.1.70205-spells"):
        for p in (FIX / d).glob("*.csv"):
            text = p.read_text(encoding="utf-8")
            if p.stem in tables:
                rows = list(csv.DictReader(io.StringIO(tables[p.stem])))
                seen = {r["ID"] for r in rows}
                extra = [r for r in csv.DictReader(io.StringIO(text)) if r["ID"] not in seen]
                out = io.StringIO()
                w = csv.DictWriter(out, list(rows[0]), lineterminator="\n")
                w.writeheader(); w.writerows(rows + extra)
                text = out.getvalue()
            tables[p.stem] = text
    return tables


TABLES = merged_tables()


class FakeHttp:
    def __init__(self, builds=BUILDS, html=HTML):
        self.builds, self.html, self.calls = builds, html, []

    def __call__(self, url):
        self.calls.append(url)
        if url == "https://wago.tools/api/builds":
            return json.dumps(self.builds)
        if url.startswith("https://wago.tools/db2/"):
            table = url.split("/db2/")[1].split("/")[0]
            return TABLES.get(table, "ID\n")             # tables the fixtures don't need: empty
        if url == "https://wowforevertalent.com/mage/":
            return self.html
        raise AssertionError(f"unexpected URL {url}")


@pytest.fixture
def data(tmp_path):
    return tmp_path / "data"


def run(data, http=None):
    http = http or FakeHttp()
    # table CSVs are saved by hand in real use (wago.tools rules); the fake serves them here
    return check_for_updates(http, data_dir=data, delay=0, now="2026-10-04T20:00:00Z", table_http_get=http)


def test_first_check_saves_a_dataset_and_reports_a_new_build(data):
    s = run(data)
    assert s.build == "1.60.1.70205"
    assert s.changed and s.previous_build is None
    ds = data / "datasets" / "1.60.1.70205.json"
    assert ds.exists()
    saved = json.loads(ds.read_text(encoding="utf-8"))
    mage = saved["classes"][0]
    assert len(mage["talents"]) == 54 and len(mage["spells"]) > 200
    assert any(t["effects"] for t in mage["talents"])            # effects attached
    assert {p["source"] for p in saved["provenance"]} == {"wago.tools", "wowforevertalent.com"}
    assert (data / "raw" / "wago" / "1.60.1.70205" / "manifest.json").exists()
    assert (data / "CHANGELOG.md").read_text(encoding="utf-8").startswith("# Data changelog\n")
    reg = json.loads((data / "builds.json").read_text(encoding="utf-8"))
    assert reg[0]["build"] == "1.60.1.70205" and reg[0]["changed"] is True


def test_summary_mentions_source_lag_and_effect_report(data):
    s = run(data)
    text = s.text()
    assert "1.60.1.70205" in text
    assert "wowforevertalent.com is on build 1.60.1.70170" in text
    # the rules follow the pinned dataset; this 70205 fixture lacks talents added since (Arcane Wrath, 70425)
    assert all("not a talent in the dataset" in p for p in s.effect_problems)


def test_second_check_with_no_changes_saves_nothing_new(data):
    run(data)
    http = FakeHttp()
    s = run(data, http)
    assert not s.changed and s.changes == []
    assert sorted(p.name for p in (data / "datasets").iterdir()) == ["1.60.1.70205.json"]
    assert not any("/db2/" in u for u in http.calls)              # cached tables reused
    assert "No talent or spell changes" in s.text()


def test_new_build_with_a_changed_talent_is_diffed_and_flags_builds(data):
    run(data)
    newer = json.loads(json.dumps(BUILDS))
    newer["wow_classic_beta"].insert(0, {"version": "1.60.1.70300", "product": "wow_classic_beta"})
    html = (HTML.replace("Increases the critical strike chance of your Fire spells by 6%",
                         "Increases the critical strike chance of your Fire spells by 9%")
            .replace("beta-20261003-adadac42", "beta-20261005-test0001"))   # site bumps its version
    s = run(data, FakeHttp(builds=newer, html=html))
    assert s.build == "1.60.1.70300" and s.previous_build == "1.60.1.70205"
    assert s.changed
    assert any("Critical Mass" in str(c) for c in s.changes)
    assert "elementalist-pve-v2" in s.affected_builds and "deep-frost" not in s.affected_builds
    assert (data / "datasets" / "1.60.1.70300.json").exists()
    log = (data / "CHANGELOG.md").read_text(encoding="utf-8")
    assert log.index("1.60.1.70300") < log.index("1.60.1.70205")


def test_cli_entry_point(data, capsys, monkeypatch):
    import wowforever.update as update
    from wowforever.__main__ import main
    monkeypatch.setattr(update, "default_http_get", FakeHttp())
    monkeypatch.setattr("wowforever.classes.CLASSES", {"mage": "wowforever.classes.mage"})  # fake serves mage only
    # no cached tables and no game-file reader: update lists what to save from wago.tools
    monkeypatch.setattr(update, "default_file_get", None)
    assert main(["update", "--data-dir", str(data), "--delay", "0"]) == 2
    out = capsys.readouterr().out
    assert "wago.tools doesn't allow automated downloads" in out and "db2/TraitNode/csv?build=1.60.1.70205" in out
    # with the tables in the cache (saved by hand; the fake stands in here) it runs
    run(data)
    assert main(["update", "--data-dir", str(data), "--delay", "0"]) == 0
    assert "1.60.1.70205" in capsys.readouterr().out


def test_popularity_saved_and_changes_reported(data):
    s = run(data)
    saved = json.loads((data / "popularity" / "mage.json").read_text(encoding="utf-8"))
    assert saved["counts"]["builds"] == 40615 and len(saved["top"]) == 5
    assert s.popular_top and not s.popular_changed
    assert "Popular community builds (unchanged)" in s.text()
    # the site reorders its top builds: the next check reports it
    swapped = HTML.replace("beta-20261003-adadac42", "beta-20261006-pop00001")
    saved["top"] = list(reversed(saved["top"]))
    (data / "popularity" / "mage.json").write_text(json.dumps(saved), encoding="utf-8")
    s2 = run(data, FakeHttp(html=swapped))
    assert s2.popular_changed and "changed since last check" in s2.text()


def test_a_new_build_points_to_patch_readiness(data):
    # #366: when a check saves a changed build, the summary names the next step; an unchanged one doesn't
    assert "patch-readiness" in run(data).text()
    assert "patch-readiness" not in run(data, FakeHttp()).text()


# ---- server hotfixes (#456) and wowforevertalents.com rank text (#458) ----

import dataclasses  # noqa: E402
import struct  # noqa: E402

from wowforever import update  # noqa: E402
from wowforever.sources import wowforevertalent  # noqa: E402


def hotfix_snapshot(root, build_number, name="1.60.1.70205-20261031"):
    """A saved hotfix snapshot with no entries: header only (XFTH, version 9, build, 32-byte hash)."""
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "DBCache.bin").write_bytes(b"XFTH" + struct.pack("<II", 9, build_number) + bytes(32))
    (folder / "manifest.json").write_text(json.dumps({"captured_at": "2026-10-31T13:15:00", "sha256": "ab" * 32}),
                                          encoding="utf-8")
    return folder


def test_hotfix_snapshot_must_be_for_the_latest_build(data, tmp_path):
    snapshot = hotfix_snapshot(tmp_path / "hf", 70707)
    with pytest.raises(ValueError, match="hotfix cache is for build 70707; the latest build is 1.60.1.70205"):
        check_for_updates(FakeHttp(), data_dir=data, delay=0, now="2026-10-04T20:00:00Z", table_http_get=FakeHttp(),
                          hotfixes=snapshot)


def test_hotfixes_change_where_tables_are_read_and_are_recorded(data, tmp_path):
    snapshot = hotfix_snapshot(tmp_path / "hf", 70205)
    http = FakeHttp()
    check_for_updates(http, data_dir=data, delay=0, now="2026-10-04T20:00:00Z", table_http_get=http,
                      hotfixes=snapshot)
    overlay = data / "cache" / "hotfixed" / "1.60.1.70205-20261031"
    assert (overlay / "TraitNode.csv").exists()
    saved = json.loads((data / "datasets" / "1.60.1.70205.json").read_text(encoding="utf-8"))
    assert {"source": "client hotfix cache", "game_build": "1.60.1.70205", "data_version": "1.60.1.70205-20261031",
            "fetched_at": "2026-10-31T13:15:00", "snapshot_sha256": "ab" * 32} in saved["provenance"]


def test_rank_text_from_wowforevertalents(data, tmp_path, monkeypatch):
    asked = []

    def fake_fetch(class_slug, *, http_get, raw_dir, delay):
        asked.append((class_slug, raw_dir, delay))
        folder = raw_dir / class_slug
        folder.mkdir(parents=True)
        manifest = folder / "manifest.json"
        manifest.write_text(json.dumps({"sha256": "cd" * 32}), encoding="utf-8")
        page = dataclasses.replace(wowforevertalent.parse_page(HTML), page_data_version="wowforevertalents-20261004",
                                   popular=None)
        return manifest, page

    monkeypatch.setattr(update.wowforevertalents, "fetch", fake_fetch)
    http = FakeHttp()
    summary = check_for_updates(http, data_dir=data, delay=0.5, now="2026-10-04T20:00:00Z", table_http_get=http,
                                rank_text_source="wowforevertalents")
    assert asked == [("mage", data / "raw" / "wowforevertalents" / "20261004", 0.5)]
    assert "https://wowforevertalent.com/mage/" not in http.calls
    saved = json.loads((data / "datasets" / "1.60.1.70205.json").read_text(encoding="utf-8"))
    assert {p["source"] for p in saved["provenance"]} == {"wago.tools", "wowforevertalents.com"}
    wft = next(p for p in saved["provenance"] if p["source"] == "wowforevertalents.com")
    assert (wft["data_version"], wft["snapshot_sha256"]) == ("wowforevertalents-20261004", "cd" * 32)
    assert summary.popular_top == [] and not (data / "popularity").exists()


def test_unknown_rank_text_source(data):
    with pytest.raises(ValueError, match="unknown rank text source 'wowhead'"):
        check_for_updates(FakeHttp(), data_dir=data, delay=0, now="2026-10-04T20:00:00Z", table_http_get=FakeHttp(),
                          rank_text_source="wowhead")


def test_cli_passes_the_hotfix_snapshot_and_rank_text_source(data, monkeypatch, capsys):
    from wowforever.__main__ import main
    seen = []

    def fake_check(http_get, **kwargs):
        seen.append({k: kwargs[k] for k in ("class_name", "hotfixes", "rank_text_source")})
        raise wago_module.MissingTables("1.60.1.70205", [], Path("x"))   # stops the CLI after one class

    from wowforever.sources import wago as wago_module
    monkeypatch.setattr(update, "check_for_updates", fake_check)
    assert main(["update", "--data-dir", str(data), "--hotfixes", "data/raw/hotfixes/x",
                 "--rank-text", "wowforevertalents"]) == 2
    assert seen == [{"class_name": "mage", "hotfixes": Path("data/raw/hotfixes/x"),
                     "rank_text_source": "wowforevertalents"}]
    assert main(["update", "--data-dir", str(data)]) == 2
    assert seen[-1] == {"class_name": "mage", "hotfixes": None, "rank_text_source": "wowforevertalent"}
