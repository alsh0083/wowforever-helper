"""wago.tools DB2 tables, as CSVs in a local cache.

wago.tools offers each DB2 table as a CSV per game build (db2/<Table>/csv?build=...), but those
download links aren't part of its published API and its robots.txt disallows them. Its published API
does serve the game files themselves (`/api/files` for file ids, `/api/casc/<id>` for a file), so with
a `file_get` `fetch_build` downloads a missing table's .db2 file and its WoWDBDefs definition and
writes the CSV itself (sources/db2.py, #234); its rows match wago.tools' CSVs cell for cell. Without
one nothing is downloaded: CSVs saved from the site in a browser into cache_dir/<build>/ are used
(`MissingTables` lists the links) and their hashes recorded in the manifest under manifest_dir.
The published `/api/builds` endpoint finds the latest build (update.py). Tests can still pass an
`http_get` to exercise the CSV download path.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


TABLES: tuple[str, ...] = (
    "Talent",
    "TalentTab",
    "Spell",
    "SpellName",
    "SpellEffect",
    "SpellMisc",
    "SpellLevels",
    "SpellCastTimes",
    "SpellPower",
    "SpellDuration",
    "SpellRange",
    "SpellCooldowns",
    "SpellTargetRestrictions",
    "SkillLineAbility",
    "SpellClassOptions",
    # Forever's talent trees are built on the Trait system; the legacy Talent table is stale.
    "TraitTree",
    "TraitNode",
    "TraitNodeEntry",
    "TraitNodeXTraitNodeEntry",
    "TraitDefinition",
    "TraitEdge",
    "TraitCond",
    "TraitNodeXTraitCond",
    "SkillLineXTraitTree",
    # gear-based placeholder stats (#68)
    "ItemSparse",
    "Item",
    "RandPropPoints",
    # weapon damage from the client's item-level tables (#129)
    "ItemDamageOneHand",
    "ItemDamageTwoHand",
    "ItemDamageRanged",
)


def _version_key(build: str) -> tuple[int, ...]:
    """Numeric sort key for a dotted build number."""
    return tuple(int(part) for part in build.split("."))


def forever_builds(builds: dict[str, list[dict[str, str]]], prefix: str = "1.60.") -> list[str]:
    """Unique `prefix` build versions across all products, sorted numerically ascending."""
    versions = {
        entry["version"]
        for entries in builds.values()
        for entry in entries
        if entry["version"].startswith(prefix)
    }
    return sorted(versions, key=_version_key)


def latest_build(builds: dict[str, list[dict[str, str]]], prefix: str = "1.60.") -> str:
    """Newest `prefix` build version (last of `forever_builds`)."""
    return forever_builds(builds, prefix)[-1]


FILES_URL = "https://wago.tools/api/files?search=dbfilesclient/&version={build}&format=csv"
CASC_URL = "https://wago.tools/api/casc/{fdid}?version={build}"
DBD_URL = "https://raw.githubusercontent.com/wowdev/WoWDBDefs/master/definitions/{table}.dbd"


def table_file_ids(listing: str) -> dict[str, int]:
    """Lowercased table name -> file id, from an `/api/files` CSV listing ("id;path" lines)."""
    out = {}
    for line in listing.splitlines():
        fid, _, path = line.partition(";")
        path = path.strip().strip('"').lower()
        if fid.isdigit() and path.startswith("dbfilesclient/") and path.endswith(".db2"):
            out[path.removeprefix("dbfilesclient/").removesuffix(".db2")] = int(fid)
    return out


def table_url(table: str, build: str) -> str:
    """CSV download URL for one DB2 table at one build."""
    return f"https://wago.tools/db2/{table}/csv?build={build}"


class MissingTables(Exception):
    """Tables for a build that must be saved from wago.tools by hand before the build can be used."""

    def __init__(self, build: str, tables: Sequence[str], build_cache: Path):
        self.build, self.tables, self.build_cache = build, list(tables), build_cache
        links = "\n".join(f"  {table_url(t, build)}  ->  {build_cache / (t + '.csv')}" for t in tables)
        super().__init__(
            f"Build {build} needs {len(tables)} table(s) that aren't cached. wago.tools doesn't allow "
            f"automated downloads of its table CSVs, so open each link in a browser and save the file "
            f"as shown, then rerun:\n{links}")


def fetch_build(
    build: str,
    *,
    http_get: Callable[[str], str] | None = None,
    cache_dir: Path,
    manifest_dir: Path,
    tables: Sequence[str] = TABLES,
    delay: float = 1.0,
    file_get: Callable[[str], bytes] | None = None,
) -> Path:
    """Make sure `tables` for `build` are in the cache, keeping a manifest record.

    A table whose cached file exists and matches the manifest hash is skipped. Without `http_get`
    (the default) missing tables are read from the game files with `file_get` when given (see the
    module docstring), else cached files saved by hand are hashed into the manifest and missing ones
    raise `MissingTables`. With `http_get`, missing tables are fetched as CSVs. Either way a refetch
    whose hash no longer matches the manifest raises `ValueError` (data changed under the same build).
    """
    build_cache = cache_dir / build
    build_raw = manifest_dir / build
    manifest_path = build_raw / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"source": "wago.tools", "build": build, "files": {}}
    )
    files: dict[str, dict[str, Any]] = manifest.setdefault("files", {})
    build_cache.mkdir(parents=True, exist_ok=True)

    def needs_fetch(table: str) -> bool:
        cached = build_cache / f"{table}.csv"
        entry = files.get(table)
        return not (
            entry is not None
            and cached.exists()
            and hashlib.sha256(cached.read_bytes()).hexdigest() == entry["sha256"]
        )

    to_fetch = [table for table in tables if needs_fetch(table)]
    to_fetch_now: list[str] = []
    if http_get is None and file_get is not None:
        for table in to_fetch:
            files[table] = _from_game_file(table, build, build_cache, file_get, files.get(table), delay)
    elif http_get is None:
        missing = [t for t in to_fetch if not (build_cache / f"{t}.csv").exists()]
        if missing:
            raise MissingTables(build, missing, build_cache)
        for table in to_fetch:                 # saved by hand: record what's there
            encoded = (build_cache / f"{table}.csv").read_bytes()
            files[table] = {"url": table_url(table, build), "sha256": hashlib.sha256(encoded).hexdigest(),
                            "bytes": len(encoded), "saved_by": "browser"}
    else:
        to_fetch_now = to_fetch
    for index, table in enumerate(to_fetch_now):
        assert http_get is not None
        if index and delay:
            time.sleep(delay)
        url = table_url(table, build)
        body = http_get(url)
        encoded = body.encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        entry = files.get(table)
        if entry is not None and digest != entry["sha256"]:
            raise ValueError(
                f"{table} data changed under build {build}: "
                f"manifest {entry['sha256'][:12]}... now {digest[:12]}..."
            )
        (build_cache / f"{table}.csv").write_bytes(encoded)
        files[table] = {"url": url, "sha256": digest, "bytes": len(encoded)}

    if to_fetch:
        build_raw.mkdir(parents=True, exist_ok=True)
        manifest["fetched_at"] = datetime.now(timezone.utc).isoformat()
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8",
                                 newline="\n")
    return manifest_path


def _from_game_file(table: str, build: str, build_cache: Path, file_get: Callable[[str], bytes],
                    entry: dict[str, Any] | None, delay: float) -> dict[str, Any]:
    """Download `table`'s .db2 for `build` and its definition, write `table`.csv, and return its
    manifest entry. The downloads are kept beside the CSV, in cache_dir/<build>/db2/."""
    from wowforever.sources import db2

    raw_dir = build_cache / "db2"
    raw_dir.mkdir(parents=True, exist_ok=True)
    listing_path = raw_dir / "files.csv"
    if not listing_path.exists():
        listing_path.write_bytes(file_get(FILES_URL.format(build=build)))
    file_ids = table_file_ids(listing_path.read_text(encoding="utf-8"))
    if table.lower() not in file_ids:
        raise ValueError(f"{table}: no dbfilesclient/{table.lower()}.db2 in build {build}'s file list")
    fdid = file_ids[table.lower()]
    if delay:
        time.sleep(delay)
    data = file_get(CASC_URL.format(fdid=fdid, build=build))
    dbd = file_get(DBD_URL.format(table=table))
    (raw_dir / f"{table}.db2").write_bytes(data)
    (raw_dir / f"{table}.dbd").write_bytes(dbd)
    encoded = db2.to_csv(data, dbd.decode("utf-8"), build).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    if entry is not None and digest != entry["sha256"]:
        raise ValueError(f"{table} data changed under build {build}: "
                         f"manifest {entry['sha256'][:12]}... now {digest[:12]}...")
    (build_cache / f"{table}.csv").write_bytes(encoded)
    return {"url": CASC_URL.format(fdid=fdid, build=build), "definition": DBD_URL.format(table=table),
            "db2_sha256": hashlib.sha256(data).hexdigest(), "sha256": digest, "bytes": len(encoded),
            "saved_by": "db2 reader"}
