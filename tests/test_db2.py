"""DB2 (WDC5) reader (#234): game files read into the CSV rows wago.tools publishes."""

import json
import struct
from pathlib import Path

from wowforever.sources import db2
from wowforever.sources.wago import CASC_URL, DBD_URL, FILES_URL, fetch_build, table_file_ids

FIXTURES = Path(__file__).parent / "fixtures" / "db2"
BUILD = "1.60.1.70205"


def fixture(name):
    return (FIXTURES / name).read_bytes()


def test_spellrange_matches_wago_csv_byte_for_byte():
    text = db2.to_csv(fixture(f"SpellRange-{BUILD}.db2"), fixture("SpellRange.dbd").decode(), BUILD)
    assert text == fixture(f"SpellRange-{BUILD}.csv").decode()


def test_floats_print_like_wago():
    bits = lambda v: struct.unpack("<I", struct.pack("<f", v))[0]
    assert db2.fmt_float(bits(1.0)) == "1"
    assert db2.fmt_float(bits(0.14)) == "0.1400000006"
    assert db2.fmt_float(bits(1.6666666)) == "1.66666662693"
    assert db2.fmt_float(bits(877.046142578125)) == "877.04614257813"   # 11 decimals, ties up
    assert db2.fmt_float(bits(1502.67236328125)) == "1502.6723632812"   # 14 digits, ties to even
    assert db2.fmt_float(bits(1e17)) == "9.9999998430675E+16"
    assert db2.fmt_float(bits(-0.0)) == "0"


def test_csv_quoting_follows_fputcsv():
    assert db2._quote("Self") == "Self"
    assert db2._quote("Self Only") == '"Self Only"'
    assert db2._quote('say "hi"') == '"say ""hi"""'
    assert db2._quote("a,b") == '"a,b"'


def test_dbd_layout_picks_the_build_and_flags():
    dbd = db2.parse_dbd(fixture("SpellRange.dbd").decode())
    schema = db2.schema_for(dbd, BUILD, 0xADA13705)
    assert schema.columns[:2] == ["ID", "DisplayName_lang"]
    assert schema.sources[0] == ("id",)
    assert schema.sources[1] == (0, 0, "t", 32) and schema.sources[4] == (3, 0, "f", 32)
    assert schema.string_fields == {0, 1}


def _sparse_file(rows):
    """A minimal sparse WDC5 file: an inline int32 ID field and a string field."""
    records = b"".join(struct.pack("<I", rid) + name.encode() + b"\0" for rid, name in rows)
    header_size = db2.HEADER.size + db2.SECTION.size + 2 * 4 + 2 * db2.STORAGE.size
    offsets, at = [], header_size
    for rid, name in rows:
        size = 4 + len(name) + 1
        offsets.append((at, size))
        at += size
    tail = b"".join(struct.pack("<IH", o, s) for o, s in offsets) + struct.pack(f"<{len(rows)}I", *(r for r, _ in rows))
    header = db2.HEADER.pack(b"WDC5", 5, b"", len(rows), 2, 0, 0, 0, 0xABCD, 0, 0, 0, 1, 0, 2, 0, 0,
                             2 * db2.STORAGE.size, 0, 0, 1)
    section = db2.SECTION.pack(0, header_size, len(rows), 0, header_size + len(records), 0, 0, len(rows), 0)
    structure = struct.pack("<hHhH", 0, 0, 0, 4)
    storage = db2.STORAGE.pack(0, 32, 0, db2.NONE, 0, 0, 0) + db2.STORAGE.pack(32, 32, 0, db2.NONE, 0, 0, 0)
    return header + section + structure + storage + records + tail


SPARSE_DBD = """COLUMNS
int ID
locstring Name_lang

LAYOUT 0000ABCD
BUILD 1.0.0.1
$id$ID<32>
Name_lang
"""


def test_sparse_tables_read_inline_strings():
    data = _sparse_file([(5, "Fire"), (9, "Frost Bolt")])
    assert db2.to_csv(data, SPARSE_DBD, "1.0.0.1") == 'ID,Name_lang\n5,Fire\n9,"Frost Bolt"\n'


def test_file_ids_come_from_the_published_listing():
    listing = '1;interface/x.blp\n1990283;dbfilesclient/spellname.db2\n7;"dbfilesclient/spell range.db2"\n'
    assert table_file_ids(listing) == {"spellname": 1990283, "spell range": 7}


def test_fetch_build_reads_missing_tables_from_game_files(tmp_path):
    calls = []

    def file_get(url):
        calls.append(url)
        if url == FILES_URL.format(build=BUILD):
            return b"1234;dbfilesclient/spellrange.db2\n"
        if url == CASC_URL.format(fdid=1234, build=BUILD):
            return fixture(f"SpellRange-{BUILD}.db2")
        if url == DBD_URL.format(table="SpellRange"):
            return fixture("SpellRange.dbd")
        raise AssertionError(url)

    cache, raw = tmp_path / "cache", tmp_path / "raw"
    manifest = fetch_build(BUILD, cache_dir=cache, manifest_dir=raw, tables=("SpellRange",), delay=0,
                           file_get=file_get)
    assert (cache / BUILD / "SpellRange.csv").read_bytes() == fixture(f"SpellRange-{BUILD}.csv")
    entry = json.loads(manifest.read_text())["files"]["SpellRange"]
    assert entry["saved_by"] == "db2 reader" and entry["url"].endswith("/1234?version=" + BUILD)
    calls.clear()
    fetch_build(BUILD, cache_dir=cache, manifest_dir=raw, tables=("SpellRange",), delay=0, file_get=file_get)
    assert calls == []                                    # cached and matching the manifest
