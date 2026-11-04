"""talentsforever.com builds page and build codes (#447).

Fixtures saved 2026-10-29 (tests/fixtures/talentsforever/README.md, CC BY 4.0). The page's top-5 rows are ranked
by activity since its window ("since the Oct 20 hotfixes to build 70425"), but the shared/saved/opened numbers
it shows count from 13 Sep, so they are kept as *_total and never feed the 20-save "settled" rule.
"""

import json
from pathlib import Path

from wowforever.sources.talentsforever import decode_build, parse_builds_page, popular_builds

FIX = Path(__file__).resolve().parent / "fixtures" / "talentsforever"
PAGE = (FIX / "mage-builds-20261029.html").read_text(encoding="utf-8")
EXPORT = json.loads((FIX / "mage-export-20261027.json").read_text(encoding="utf-8"))


def test_the_page_names_its_window_and_the_build_it_starts_on():
    page = parse_builds_page(PAGE)
    assert page["window"] == "since the Oct 20 hotfixes to build 70425"
    assert page["window_build"] == "70425"


def test_the_top_five_rows_in_page_order():
    rows = parse_builds_page(PAGE)["top"]
    assert [r["rank"] for r in rows] == [1, 2, 3, 4, 5]
    # row 1: "Arcane Mage 47/4/0 ... shared 60 · saved 168 · opened 1,033 · across 47 close builds"
    assert rows[0] == {
        "rank": 1, "name": "Arcane Mage 47/4/0", "points": [47, 4, 0],
        "shared_total": 60, "saved_total": 168, "opened_total": 1033, "variants": 47,
        "code": "2551225223122301531-13--8",
    }
    # row 5: "Fire / Arcane Mage 21/28/2 ... shared 8 · saved 7 · opened 1,756 · across 11 close builds"
    assert rows[4]["name"] == "Fire / Arcane Mage 21/28/2"
    assert (rows[4]["shared_total"], rows[4]["saved_total"], rows[4]["opened_total"], rows[4]["variants"]) == \
        (8, 7, 1756, 11)
    assert rows[2]["code"] == "--053532333121331251-8"
    assert not any("saved" in r for r in rows)     # only the 13-Sep totals, under their own names


def test_decode_reads_one_digit_per_talent_in_export_order():
    # Arcane tree digits 2551225223122301531: Wand Specialization 2, Arcane Focus 5, Improved Channeling 5,
    # Missile Barrage 1, ...; Fire "13": Improved Fire Blast 1, Incineration 3; Frost empty; trailing "8" ignored
    final = decode_build("2551225223122301531-13--8", EXPORT)
    assert sum(final.values()) == 51
    assert final["Wand Specialization"] == 2 and final["Improved Channeling"] == 5
    assert final["Missile Barrage"] == 1 and final["Arcane Power"] == 1
    assert final["Improved Fire Blast"] == 1 and final["Incineration"] == 3
    assert 0 not in final.values()                  # untaken talents are left out


def test_decode_reads_the_70685_frost_tree():
    # Frost digits 053532333121331251 in export order: Frost Warding 0, Improved Frostbolt 5, Elemental Precision 3,
    # Ice Shards 5, Frostbite 3, Improved Frost Nova 2, Permafrost 3, Frost Channeling 3, Improved Blizzard 3,
    # Ice Lance 1, Arctic Reach 2, Ice Block 1, Shatter 3, Improved Cone of Cold 3, Cold Snap 1,
    # Fingers of Frost 2, Winter's Chill 5, Ice Barrier 1
    final = decode_build("--053532333121331251-8", EXPORT)
    assert sum(final.values()) == 46
    assert final["Elemental Precision"] == 3 and final["Winter's Chill"] == 5 and final["Ice Barrier"] == 1
    assert "Frost Warding" not in final and "Piercing Ice" not in final


def test_popular_builds_carry_the_decoded_talents():
    builds = popular_builds(PAGE, EXPORT)
    assert len(builds) == 5
    fire = builds[3]
    assert fire["rank"] == 4 and fire["points"] == [16, 32, 3] and fire["saved_total"] == 17
    assert fire["final"]["Critical Mass"] == 5 and fire["final"]["Combustion"] == 1
    assert sum(fire["final"].values()) == 51
    assert "code" in fire and "name" in fire


# ---- snapshots (#460): builds pages and exports saved gzipped, immutable, checked on load ----

class FakeSite:
    def __init__(self):
        self.asked = []

    def __call__(self, url):
        self.asked.append(url)
        if url.endswith("/mage/builds"):
            return PAGE
        if url.endswith("/export/mage.json"):
            return json.dumps(EXPORT)
        raise AssertionError(f"unexpected {url}")


def test_fetch_saves_each_class_once_and_load_reads_it_back(tmp_path):
    from wowforever.sources.talentsforever import fetch, latest_snapshot, load_snapshot

    site, naps = FakeSite(), []
    manifest = fetch(http_get=site, raw_dir=tmp_path / "20261104", classes=("mage",), sleep=naps.append)
    assert site.asked == ["https://talentsforever.com/mage/builds", "https://talentsforever.com/export/mage.json"]
    assert naps == [1.5]
    assert sorted(p.name for p in (tmp_path / "20261104").iterdir()) == [
        "builds-mage.html.gz", "export-mage.json.gz", "manifest.json"]
    saved = json.loads(manifest.read_text(encoding="utf-8"))
    assert (saved["source"], saved["captured"], saved["classes"], saved["files"], saved["license"]) == (
        "talentsforever.com", "2026-11-04", ["mage"], 2, "CC BY 4.0")
    assert load_snapshot(tmp_path / "20261104") == {"mage": (PAGE, EXPORT)}
    assert latest_snapshot(tmp_path) == tmp_path / "20261104" and latest_snapshot(tmp_path / "none") is None

    def offline(url):
        raise AssertionError(f"fetched {url}")

    assert fetch(http_get=offline, raw_dir=tmp_path / "20261104", classes=("mage",)) == manifest


def test_load_snapshot_refuses_edited_pages(tmp_path):
    import gzip

    import pytest

    from wowforever.sources.talentsforever import fetch, load_snapshot

    fetch(http_get=FakeSite(), raw_dir=tmp_path / "20261104", classes=("mage",), sleep=lambda s: None)
    page = tmp_path / "20261104" / "builds-mage.html.gz"
    page.write_bytes(gzip.compress(b"edited", mtime=0))
    with pytest.raises(ValueError, match="pages changed since the snapshot was saved"):
        load_snapshot(tmp_path / "20261104")
