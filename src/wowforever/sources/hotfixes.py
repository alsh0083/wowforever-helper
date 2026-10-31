"""The game client's hotfix cache (DBCache.bin, XFTH version 9), laid over a build's tables (#456).

The realm sends hotfix rows at character select; the client keeps them in Cache/ADB/<locale>/DBCache.bin.
"""

from __future__ import annotations

import csv
import io
import struct
from collections.abc import Iterable
from dataclasses import dataclass

from wowforever.sources import db2

FILE_HEADER_SIZE = 44
ENTRY = struct.Struct("<4siiIIIiB3x")     # magic, region, push id, unique id, table hash, record id, size, status
VALID, REMOVED = 1, 2


@dataclass(frozen=True)
class Hotfix:
    push_id: int
    unique_id: int
    table_hash: int
    record_id: int
    status: int
    data: bytes


def read_cache(data: bytes) -> tuple[int, list[Hotfix]]:
    """(game build number, every entry in file order) from a DBCache.bin file."""
    if data[:4] != b"XFTH":
        raise ValueError("not a hotfix cache: no XFTH magic")
    version, build = struct.unpack_from("<II", data, 4)
    if version != 9:
        raise ValueError(f"unsupported hotfix cache version {version} (expected 9)")
    hotfixes = []
    pos = FILE_HEADER_SIZE
    while pos < len(data):
        if pos + ENTRY.size > len(data):
            raise ValueError(f"truncated hotfix cache: entry header at byte {pos}")
        magic, _region, push_id, unique_id, table_hash, record_id, size, status = ENTRY.unpack_from(data, pos)
        start = pos + ENTRY.size
        if magic != b"XFTH" or size < 0 or start + size > len(data):
            raise ValueError(f"truncated hotfix cache: entry at byte {pos}")
        hotfixes.append(Hotfix(push_id, unique_id, table_hash, record_id, status, data[start:start + size]))
        pos = start + size
    return build, hotfixes


def latest(hotfixes: Iterable[Hotfix]) -> dict[tuple[int, int], Hotfix]:
    """The newest entry per (table hash, record id); on equal push ids the later entry wins."""
    picked: dict[tuple[int, int], Hotfix] = {}
    for hotfix in hotfixes:
        key = (hotfix.table_hash, hotfix.record_id)
        if key not in picked or hotfix.push_id >= picked[key].push_id:
            picked[key] = hotfix
    return picked


def decode_row(data: bytes, schema: db2.Schema) -> dict[str, str]:
    """One hotfix row as {column: CSV text}, without the non-inline ID column."""
    row: dict[str, str] = {}
    pos = 0
    for column, source in zip(schema.columns, schema.sources):
        if source == ("id",):
            continue
        kind, bits = ("u", 32) if source == ("rel",) else (source[2], source[3])
        if kind == "t":
            end = data.find(b"\0", pos)
            if end < 0:
                raise ValueError(f"row data too short for {column}")
            row[column] = data[pos:end].decode("utf-8", errors="replace")
            pos = end + 1
            continue
        width = bits // 8
        if pos + width > len(data):
            raise ValueError(f"row data too short for {column}")
        raw = int.from_bytes(data[pos:pos + width], "little")
        pos += width
        if kind == "f":
            row[column] = db2.fmt_float(raw)
        elif kind == "s":
            row[column] = str(db2._signed(raw, bits))
        else:
            row[column] = str(raw)
    if pos != len(data):
        left = len(data) - pos
        raise ValueError(f"{left} byte{'' if left == 1 else 's'} left over after the last column")
    return row


def apply_csv(csv_text: str, schema: db2.Schema, table_hash: int, hotfixes: Iterable[Hotfix]) -> str:
    """A wago-style table CSV with this table's hotfixes applied: valid rows replace the row with the same
    ID in place or are appended in ID order, removed records are dropped, other statuses change nothing."""
    rows = list(csv.reader(io.StringIO(csv_text)))
    header, body = rows[0], rows[1:]
    id_column = header.index("ID")
    by_id = {row[id_column]: row for row in body}
    added: list[tuple[int, list[str]]] = []
    for (hash_, record_id), hotfix in latest(hotfixes).items():
        if hash_ != table_hash:
            continue
        key = str(record_id)
        if hotfix.status == REMOVED:
            by_id.pop(key, None)
            continue
        if hotfix.status != VALID:
            continue
        values = decode_row(hotfix.data, schema)
        values.setdefault("ID", key)
        row = [values[column] for column in header]
        if key in by_id:
            by_id[key] = row
        else:
            added.append((record_id, row))
    out = [header, *by_id.values(), *(row for _, row in sorted(added))]
    return "".join(",".join(db2._quote(value) for value in row) + "\n" for row in out)
