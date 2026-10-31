"""Server hotfixes from the client's DBCache.bin, laid over a build's tables (#456)."""

import struct
from pathlib import Path

import pytest

from wowforever.sources import db2
from wowforever.sources.hotfixes import Hotfix, apply_csv, decode_row, latest, read_cache

FIX = Path(__file__).resolve().parent / "fixtures" / "hotfixes"
BUILD = "1.60.1.70707"
SPELLNAME, TRAITNODE = 0x46C66698, 0xE1432D63


def schema(name, layout):
    return db2.schema_for(db2.parse_dbd((FIX / f"{name}.dbd").read_text(encoding="utf-8")), BUILD, layout)


def sample():
    return read_cache((FIX / "DBCache-sample.bin").read_bytes())


def test_read_cache_gives_the_build_and_every_entry_in_file_order():
    build, hotfixes = sample()
    assert build == 70707
    assert [(h.table_hash, h.record_id, h.push_id, h.status, len(h.data)) for h in hotfixes] == [
        (0xAE1CA308, 580844, 112618, 3, 0),
        (SPELLNAME, 1326589, 112635, 4, 0),
        (TRAITNODE, 105773, 112753, 2, 0),
        (SPELLNAME, 2118, 112758, 2, 0),
        (SPELLNAME, 468843, 112758, 1, 9),
        (TRAITNODE, 104951, 113283, 1, 25),
    ]
    assert hotfixes[4].data == b"Lacerate\0"
    assert hotfixes[0].unique_id == 0x86_6F_05_0E


def test_read_cache_refuses_other_files():
    data = (FIX / "DBCache-sample.bin").read_bytes()
    with pytest.raises(ValueError, match="XFTH"):
        read_cache(b"WDC5" + data[4:])
    with pytest.raises(ValueError, match="version 8"):
        read_cache(data[:4] + struct.pack("<I", 8) + data[8:])
    with pytest.raises(ValueError, match="truncated"):
        read_cache(data[:-3])


def h(push, record, status=1, data=b"", table=SPELLNAME):
    return Hotfix(push_id=push, unique_id=0, table_hash=table, record_id=record, status=status, data=data)


def test_latest_keeps_the_newest_push_per_record():
    old, new, other = h(5, 10, data=b"A\0"), h(7, 10, status=2), h(6, 11, data=b"B\0")
    later_same_push = h(7, 10, data=b"C\0")
    picked = latest([new, old, other, later_same_push])
    assert picked == {(SPELLNAME, 10): later_same_push, (SPELLNAME, 11): other}


def test_decode_spellname_row_skips_the_noninline_id():
    assert decode_row(b"Lacerate\0", schema("SpellName", 0x782EE721)) == {"Name_lang": "Lacerate"}


def test_decode_traitnode_row_reads_declared_widths_and_the_relation_in_place():
    # f7990100 | 41040000 | 4c180000 | 5a0f0000 | 00 | 00000000 | 00000000
    # ID 104951, TraitTreeID 1089 (druid), PosX 6220, PosY 3930 (row 4), Type u8 0, Flags 0, TraitSubTreeID 0
    _, hotfixes = sample()
    row = decode_row(hotfixes[5].data, schema("TraitNode", 0xA01A518A))
    assert row == {"ID": "104951", "TraitTreeID": "1089", "PosX": "6220", "PosY": "3930", "Type": "0",
                   "Flags": "0", "TraitSubTreeID": "0"}


def test_decode_row_signs_floats_and_rejects_leftover_bytes():
    s = db2.Schema(["ID", "A", "B", "C"], [("id",), (0, 0, "s", 16), (1, 0, "f", 32), (2, 0, "u", 8)])
    data = struct.pack("<hfB", -2, 0.5, 200)
    assert decode_row(data, s) == {"A": "-2", "B": "0.5", "C": "200"}
    with pytest.raises(ValueError, match="1 byte"):
        decode_row(data + b"\0", s)
    with pytest.raises(ValueError, match="short"):
        decode_row(data[:-1], s)


SPELLNAME_CSV = 'ID,Name_lang\n2118,"Lacerate (old)"\n9999,Rake\n468843,Old\n'


def test_apply_csv_replaces_removes_and_appends_rows():
    _, hotfixes = sample()
    s = schema("SpellName", 0x782EE721)
    out = apply_csv(SPELLNAME_CSV, s, SPELLNAME, hotfixes)
    # 2118 removed (status 2); 468843 replaced in place; 1326589 is status 4 and changes nothing
    assert out == "ID,Name_lang\n9999,Rake\n468843,Lacerate\n"


def test_apply_csv_appends_new_records_in_id_order_and_keeps_inline_ids():
    _, hotfixes = sample()
    s = schema("TraitNode", 0xA01A518A)
    base = "ID,TraitTreeID,PosX,PosY,Type,Flags,TraitSubTreeID\n105773,1089,1,1,0,0,0\n"
    new = h(9, 104950, data=struct.pack("<IIIIBII", 104950, 1089, 5620, 3930, 0, 0, 0), table=TRAITNODE)
    out = apply_csv(base, s, TRAITNODE, hotfixes + [new])
    assert out == ("ID,TraitTreeID,PosX,PosY,Type,Flags,TraitSubTreeID\n"
                   "104950,1089,5620,3930,0,0,0\n"
                   "104951,1089,6220,3930,0,0,0\n")


def test_apply_csv_ignores_other_tables_and_quotes_like_wago():
    s = schema("SpellName", 0x782EE721)
    other = h(1, 5, data=b"x\0", table=TRAITNODE)
    added = h(2, 7, data=b"Shield, Sworn\0")
    assert apply_csv("ID,Name_lang\n", s, SPELLNAME, [other, added]) == 'ID,Name_lang\n7,"Shield, Sworn"\n'
