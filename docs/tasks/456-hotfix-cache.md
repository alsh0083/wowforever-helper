# Task #456 (part A): read the client's hotfix cache and lay it over a table

Make `tests/test_hotfixes.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Create exactly one file: `src/wowforever/sources/hotfixes.py`. Edit no other file.
- Before you start, `tests/test_hotfixes.py` fails at import: the module doesn't exist yet. Nothing else should fail.
- Run `.venv/Scripts/python -m pytest tests/test_hotfixes.py -q` after each step, then the fast suite once at the end.

## Why
The realm sends hotfix rows to the game client at character select, and the client saves them in `DBCache.bin`.
The druid/paladin rework (#455) exists only there. This module reads that file and applies its rows to a table's
CSV text, so later work (#456 part B) can save a dataset of "build 70707 + hotfixes".

## File format (XFTH version 9)
- File header, 44 bytes: magic `b"XFTH"`, version (u32, must be 9), build (u32), 32-byte hash.
- Then entries until the end of the file. Entry header, 32 bytes, struct format `"<4siiIIIiB3x"`: magic `b"XFTH"`,
  region (i32), push id (i32), unique id (u32), table hash (u32), record id (u32), data size (i32), status (u8),
  3 padding bytes. Then `data size` bytes of row data.
- Status: 1 valid row, 2 record removed, 3 invalid, 4 not public. Only 1 and 2 change a table.
- Row data: the table's columns in `db2.Schema` order. A `("id",)` source (non-inline ID) is NOT in the data.
  A `("rel",)` source is a u32 in place. Any other source `(index, element, kind, bits)` takes `bits // 8` bytes,
  little-endian; kind `"t"` is instead a null-terminated UTF-8 string. Kind `"f"` is printed with `db2.fmt_float(raw)`,
  `"s"` with `db2._signed(raw, bits)`, `"u"` as the plain integer.

## Step 1: create `src/wowforever/sources/hotfixes.py` with the header, `Hotfix` and `read_cache`
```python
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
```
Run the test file: the two `read_cache` tests pass.

## Step 2: add `latest` after `read_cache`
```python
def latest(hotfixes: Iterable[Hotfix]) -> dict[tuple[int, int], Hotfix]:
    """The newest entry per (table hash, record id); on equal push ids the later entry wins."""
    picked: dict[tuple[int, int], Hotfix] = {}
    for hotfix in hotfixes:
        key = (hotfix.table_hash, hotfix.record_id)
        if key not in picked or hotfix.push_id >= picked[key].push_id:
            picked[key] = hotfix
    return picked
```

## Step 3: add `decode_row` after `latest`
```python
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
```

## Step 4: add `apply_csv` at the end of the file
```python
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
```

## Done when
- `tests/test_hotfixes.py` passes (9 tests); the fast suite has no other new failures.
- Only `src/wowforever/sources/hotfixes.py` is new; no other file changed.
