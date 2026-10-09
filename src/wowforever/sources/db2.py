"""DB2 (WDC5) reader for the game client's tables, fetched through wago.tools' published file API (#234).

wago.tools' robots.txt disallows its /db2/ CSV downloads, but its published API serves the raw game files
(`/api/casc/{fdid}?version=...`, file ids from `/api/files`). This module parses those files into the same
rows the CSVs had, so `update` can fetch a new build's tables itself.

A WDC5 file: a header, one header per section, the field structure and storage info, pallet and common
data blocks, then each section's records, string table, id list, copy table and relationship map. Field
values are stored plain, bitpacked (signed or not), as a per-id "common" default, or as an index into a
pallet (of single values or arrays). Strings are offsets relative to the field's own position.
Encrypted sections whose key the file service doesn't ship come back zeroed and are skipped.

Column names and types come from a schema (`Schema`): the names of the expanded columns in field order
and which are floats, strings or signed. Schemas are inferred from a build whose CSVs we already have
(see `infer_schema`) and kept per table layout hash.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Context, Decimal
import re
import struct
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

HEADER = struct.Struct("<4sI128s9I2H7I")       # magic, version, schema string, counts..., section count
SECTION = struct.Struct("<Q8I")                 # tact key hash, file offset, record count, ...
STORAGE = struct.Struct("<HHIIIII")             # offset bits, size bits, extra size, type, three values

NONE, BITPACKED, COMMON, PALLET, PALLET_ARRAY, BITPACKED_SIGNED = range(6)


@dataclass
class Field:
    offset_bits: int
    size_bits: int
    extra_size: int
    kind: int
    values: tuple[int, int, int]
    element_bits: int                           # from the field structure (32 - size)
    count: int = 1                              # array length
    pallet: list[int] = field(default_factory=list)
    common: dict[int, int] = field(default_factory=dict)


@dataclass
class Table:
    layout_hash: int
    table_hash: int
    fields: list[Field]
    rows: list[tuple[int, list[list[int]], int | None, int]]   # (id, raw values per field, relation, record index)
    strings: dict[int, str]                                # string table position -> string
    record_size: int
    has_relation: bool


def _signed(value: int, bits: int) -> int:
    return value - (1 << bits) if bits and value & (1 << (bits - 1)) else value


def layout_hash(data: bytes) -> int:
    """The table layout hash from a WDC5 file's header (picks the schema to read it with)."""
    return HEADER.unpack_from(data, 0)[8]


def parse(data: bytes, string_fields: frozenset[int] = frozenset()) -> Table:
    """Parse a WDC5 file. Sparse tables keep strings inline, so reading one needs `string_fields`
    (the indexes of its string fields, from the schema); their string values come back as `str`."""
    (magic, _version, _schema, record_count, field_count, record_size, string_table_size, table_hash,
     layout_hash, _min_id, _max_id, _locale, flags, id_index, total_field_count, _bitpacked_offset,
     _lookup_columns, storage_size, common_size, pallet_size, section_count) = HEADER.unpack_from(data, 0)
    if magic != b"WDC5":
        raise ValueError(f"not a WDC5 file: {magic!r}")
    sparse = bool(flags & 1)
    pos = HEADER.size
    sections = [SECTION.unpack_from(data, pos + i * SECTION.size) for i in range(section_count)]
    pos += section_count * SECTION.size
    structure = [struct.unpack_from("<hH", data, pos + i * 4) for i in range(total_field_count)]
    pos += total_field_count * 4
    fields = []
    for i in range(storage_size // STORAGE.size):
        off, size, extra, kind, a, b, c = STORAGE.unpack_from(data, pos + i * STORAGE.size)
        bits = 32 - structure[i][0] if i < len(structure) else 32
        f = Field(off, size, extra, kind, (a, b, c), bits)
        if kind == NONE:
            f.count = max(1, size // bits) if bits else 1
        elif kind == PALLET_ARRAY:
            f.count = c
        fields.append(f)
    pos += storage_size
    for f in fields:                              # pallet blocks, in field order
        if f.kind in (PALLET, PALLET_ARRAY):
            f.pallet = list(struct.unpack_from(f"<{f.extra_size // 4}I", data, pos))
            pos += f.extra_size
    for f in fields:                              # common data blocks, in field order
        if f.kind == COMMON:
            pairs = struct.unpack_from(f"<{f.extra_size // 4}I", data, pos)
            f.common = dict(zip(pairs[0::2], pairs[1::2]))
            pos += f.extra_size

    rows: list[tuple[int, list[list[int]], int | None, int]] = []
    strings: dict[int, str] = {}
    string_base = 0
    global_index = 0
    total_records = sum(s[2] for s in sections)
    has_relation = any(s[6] for s in sections)
    for (key_hash, file_offset, n, str_size, records_end, id_list_size, rel_size, map_count,
         copy_count) in sections:
        if sparse:
            rows.extend(_sparse_section(data, fields, string_fields, id_index, file_offset, records_end,
                                        id_list_size, rel_size, map_count, copy_count))
            continue
        records_start = file_offset
        strings_start = records_start + n * record_size
        block = data[strings_start:strings_start + str_size]
        if key_hash and not any(data[records_start:records_start + n * record_size]):
            global_index += n                     # encrypted and not shipped: skip, keep positions aligned
            string_base += str_size
            continue
        i = 0
        while i < len(block):
            j = block.index(b"\0", i)
            strings[string_base + i] = block[i:j].decode("utf-8", errors="replace")
            i = j + 1
        p = strings_start + str_size
        ids = list(struct.unpack_from(f"<{id_list_size // 4}I", data, p)) if id_list_size else []
        p += id_list_size
        copies = [struct.unpack_from("<II", data, p + k * 8) for k in range(copy_count)]
        p += copy_count * 8
        relation: dict[int, int] = {}
        if rel_size:
            entries, _rmin, _rmax = struct.unpack_from("<3I", data, p)
            for k in range(entries):
                foreign, index = struct.unpack_from("<II", data, p + 12 + k * 8)
                relation[index] = foreign
        section_rows = []
        for r in range(n):
            raw = int.from_bytes(data[records_start + r * record_size:records_start + (r + 1) * record_size], "little")
            values = []
            for f in fields:
                if f.kind == NONE:
                    values.append([(raw >> (f.offset_bits + k * f.element_bits)) & ((1 << f.element_bits) - 1)
                                   for k in range(f.count)])
                    continue
                packed = (raw >> f.offset_bits) & ((1 << f.values[1]) - 1) if f.kind != COMMON else 0
                if f.kind == BITPACKED:
                    values.append([packed])
                elif f.kind == BITPACKED_SIGNED:
                    values.append([_signed(packed, f.values[1])])
                elif f.kind == PALLET:
                    values.append([f.pallet[packed]])
                elif f.kind == PALLET_ARRAY:
                    values.append([f.pallet[packed * f.count + k] for k in range(f.count)])
                else:
                    values.append([None])          # common: filled once the id is known
            rid = ids[r] if ids else values[id_index][0]
            for k, f in enumerate(fields):
                if f.kind == COMMON:
                    values[k] = [f.common.get(rid, f.values[0])]
            section_rows.append((rid, values, relation.get(r), global_index + r))
        by_id = {row[0]: row for row in section_rows}
        for new_id, old_id in copies:
            if old_id in by_id:
                old = by_id[old_id]
                section_rows.append((new_id, old[1], old[2], old[3]))
        rows.extend(section_rows)
        global_index += n
        string_base += str_size
    table = Table(layout_hash, table_hash, fields, rows, strings, record_size, has_relation)
    table._total_records = total_records          # type: ignore[attr-defined]
    return table


def _sparse_section(data: bytes, fields: list[Field], string_fields: frozenset[int], id_index: int,
                    start: int, records_end: int, id_list_size: int, rel_size: int, map_count: int,
                    copy_count: int) -> list[tuple[int, list[list[Any]], int | None, int]]:
    """One section of a sparse table: variable-length records found through the offset map, fields
    byte-aligned, strings inline."""
    p = records_end
    ids = list(struct.unpack_from(f"<{id_list_size // 4}I", data, p)) if id_list_size else []
    p += id_list_size
    copies = [struct.unpack_from("<II", data, p + k * 8) for k in range(copy_count)]
    p += copy_count * 8
    offsets = [struct.unpack_from("<IH", data, p + k * 6) for k in range(map_count)]
    p += map_count * 6
    relation: dict[int, int] = {}
    if rel_size:
        entries = struct.unpack_from("<I", data, p)[0]
        for k in range(entries):
            foreign, index = struct.unpack_from("<II", data, p + 12 + k * 8)
            relation[index] = foreign
        p += rel_size
    sparse_ids = list(struct.unpack_from(f"<{map_count}I", data, p))
    ids = ids or sparse_ids
    rows = []
    for r, (offset, size) in enumerate(offsets):
        if not size:
            continue
        q, values = offset, []
        for i, f in enumerate(fields):
            elems: list[Any] = []
            for _k in range(f.count):
                if i in string_fields:
                    end = data.index(b"\0", q)
                    elems.append(data[q:end].decode("utf-8", errors="replace"))
                    q = end + 1
                else:
                    width = f.element_bits // 8
                    elems.append(int.from_bytes(data[q:q + width], "little"))
                    q += width
            values.append(elems)
        rid = ids[r] if r < len(ids) else values[id_index][0]
        rows.append((rid, values, relation.get(r), -1))
    by_id = {row[0]: row for row in rows}
    for new_id, old_id in copies:
        if old_id in by_id:
            rows.append((new_id, *by_id[old_id][1:]))
    return rows


def string_at(table: Table, global_index: int, field_index: int, element: int, value: int) -> str | None:
    """The string a string field's stored offset points to (offsets are relative to the field's own
    position in the concatenated record data)."""
    if value == 0:
        return ""                                  # offset 0: an empty string
    f = table.fields[field_index]
    field_byte = (f.offset_bits + element * f.element_bits) // 8
    pos = global_index * table.record_size + field_byte + value - table._total_records * table.record_size  # type: ignore[attr-defined]
    return table.strings.get(pos)




# --- column names and types from WoWDBDefs (.dbd), and the CSV text wago.tools would print ------------

@dataclass
class DbdEntry:
    name: str
    noninline_id: bool = False
    relation: bool = False
    inline_id: bool = False
    bits: int = 32
    unsigned: bool = False
    count: int = 1


@dataclass
class DbdLayout:
    hashes: set[str]
    builds: list[str]                   # single builds and "a-b" ranges
    entries: list[DbdEntry]


@dataclass
class Dbd:
    types: dict[str, str]               # column name -> int | float | string | locstring
    layouts: list[DbdLayout]


_ENTRY = re.compile(r"^(?:\$([^$]+)\$)?([A-Za-z_][\w]*)(?:<(u?)(\d+)>)?(?:\[(\d+)\])?")


def parse_dbd(text: str) -> Dbd:
    """A WoWDBDefs definition file: its COLUMNS types and its LAYOUT/BUILD blocks."""
    types: dict[str, str] = {}
    layouts: list[DbdLayout] = []
    blocks = [b.strip().splitlines() for b in re.split(r"\n\s*\n", text.replace("\r", "")) if b.strip()]
    for block in blocks:
        if block[0].strip() == "COLUMNS":
            for line in block[1:]:
                line = line.split("//")[0].strip()
                if line:
                    kind, name = line.split()[:2]
                    types[name.rstrip("?")] = kind.split("<")[0]
            continue
        current = DbdLayout(set(), [], [])
        for line in block:
            line = line.split("//")[0].strip()
            if line.startswith("LAYOUT"):
                current.hashes |= {h.strip().lower() for h in line[6:].split(",")}
            elif line.startswith("BUILD"):
                current.builds += [b.strip() for b in line[5:].split(",")]
            elif line.startswith("COMMENT") or not line:
                continue
            else:
                m = _ENTRY.match(line)
                if not m:
                    raise ValueError(f"unreadable .dbd line: {line!r}")
                flags = set((m.group(1) or "").split(","))
                current.entries.append(DbdEntry(
                    m.group(2), noninline_id="noninline" in flags and "id" in flags,
                    relation="relation" in flags and "noninline" in flags, inline_id="id" in flags and "noninline" not in flags,
                    bits=int(m.group(4) or 32), unsigned=m.group(3) == "u", count=int(m.group(5) or 1)))
        if current.entries:
            layouts.append(current)
    return Dbd(types, layouts)


def _version(build: str) -> tuple[int, ...]:
    return tuple(int(p) for p in build.split("."))


def _covers(builds: Sequence[str], build: str) -> bool:
    v = _version(build)
    for b in builds:
        if "-" in b:
            lo, hi = b.split("-")
            if _version(lo) <= v <= _version(hi):
                return True
        elif b == build:
            return True
    return False


@dataclass
class Schema:
    """How one table layout's fields become CSV columns: per column, where its value comes from."""
    columns: list[str]
    sources: list[tuple]                # ("id",) | ("rel",) | (field index, element, kind u|s|f|t, bits)

    @property
    def string_fields(self) -> frozenset[int]:
        return frozenset(s[0] for s in self.sources if len(s) == 4 and s[2] == "t")


def schema_for(dbd: Dbd, build: str, layout: int) -> Schema:
    """The schema for `build` (or, failing that, for the file's `layout` hash) from a parsed .dbd."""
    want = f"{layout:08x}"
    match = next((l for l in dbd.layouts if _covers(l.builds, build) and (not l.hashes or want in l.hashes)),
                 None) or next((l for l in dbd.layouts if want in l.hashes), None)
    if match is None:
        raise ValueError(f"no .dbd layout for build {build} / layout {want}")
    columns: list[str] = []
    sources: list[tuple] = []
    index = 0
    for e in match.entries:
        if e.noninline_id:
            columns.append(e.name)
            sources.append(("id",))
            continue
        if e.relation:
            columns.append(e.name)
            sources.append(("rel",))
            continue
        kind = dbd.types.get(e.name, "int")
        code = {"float": "f", "string": "t", "locstring": "t"}.get(kind, "u" if e.unsigned else "s")
        base = _RENAMED.get(e.name, e.name)
        for k in range(e.count):
            columns.append(f"{base}_{k}" if e.count > 1 else base)
            sources.append((index, k, code, e.bits))
        index += 1
    return Schema(columns, sources)


_WIDE = Context(prec=80)
_RENAMED = {"Index": "_Index"}          # wago.tools prefixes column names that are SQL keywords


def fmt_float(bits: int) -> str:
    """A float32 as wago.tools' CSVs print it: rounded half up to 11 decimals, then printed with 14
    significant digits (exponent form past that, e.g. 9.9999998430675E+16)."""
    v = Decimal(struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0])
    if not v.is_finite():
        return str(float(v))
    v = v.quantize(Decimal("1e-11"), ROUND_HALF_UP, _WIDE)       # PHP-style round(): ties go up
    text = format(float(v), ".14G")                               # printf: exact binary, ties to even
    return "0" if text == "-0" else text


def _cell(table: Table, gi: int, source: tuple, values: list[list[Any]]) -> str:
    i, k, code, bits = source
    raw = values[i][k]
    if isinstance(raw, str):
        return raw
    if code == "t":
        return (string_at(table, gi, i, k, raw) or "") if gi >= 0 else ""
    if code == "f":
        return fmt_float(raw)
    raw &= (1 << bits) - 1
    return str(_signed(raw, bits) if code == "s" else raw)


def rows_as_text(table: Table, schema: Schema) -> list[list[str]]:
    """The table as CSV rows (without the header), in file order."""
    if len({s[0] for s in schema.sources if len(s) == 4}) != len(table.fields):
        raise ValueError(f"schema has {len(schema.sources)} fields; the file has {len(table.fields)}")
    out = []
    for rid, values, rel, gi in table.rows:
        out.append([str(rid) if s[0] == "id" else str(rel or 0) if s[0] == "rel" else _cell(table, gi, s, values)
                    for s in schema.sources])
    return out


def to_csv(data: bytes, dbd_text: str, build: str) -> str:
    """A DB2 file as wago.tools-style CSV text (header row, LF line ends)."""
    schema = schema_for(parse_dbd(dbd_text), build, layout_hash(data))
    table = parse(data, schema.string_fields)
    return "".join(",".join(_quote(v) for v in row) + "\n" for row in [schema.columns, *rows_as_text(table, schema)])


_NEEDS_QUOTES = re.compile(r'[,"\s]')


def _quote(value: str) -> str:
    """CSV quoting as PHP's fputcsv does it (and so wago.tools): quote anything with a comma, a quote or
    whitespace in it."""
    return '"' + value.replace('"', '""') + '"' if _NEEDS_QUOTES.search(value) else value
