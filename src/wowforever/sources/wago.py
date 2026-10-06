"""wago.tools DB2 table CSVs, read from a local cache.

wago.tools offers each DB2 table as a CSV per game build (db2/<Table>/csv?build=...), but those
download links aren't part of its published API and its robots.txt disallows them. So by default
this module downloads nothing: a person saves the CSVs from the site in a browser into
cache_dir/<build>/ (`MissingTables` lists the links), and `fetch_build` records their hashes in the
manifest under manifest_dir. The published `/api/builds` endpoint, used to find the latest build,
stays automated (update.py). Tests can still pass an `http_get` to exercise the download path.
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
) -> Path:
    """Make sure `tables` for `build` are in the cache, keeping a manifest record.

    A table whose cached file exists and matches the manifest hash is skipped. Without `http_get`
    (the default) nothing is downloaded: cached files saved by hand are hashed into the manifest,
    and missing ones raise `MissingTables`. With `http_get`, missing tables are fetched; a refetch
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
    if http_get is None:
        missing = [t for t in to_fetch if not (build_cache / f"{t}.csv").exists()]
        if missing:
            raise MissingTables(build, missing, build_cache)
        for table in to_fetch:                 # saved by hand: record what's there
            encoded = (build_cache / f"{table}.csv").read_bytes()
            files[table] = {"url": table_url(table, build), "sha256": hashlib.sha256(encoded).hexdigest(),
                            "bytes": len(encoded), "saved_by": "browser"}
        to_fetch_now: list[str] = []
    else:
        to_fetch_now = to_fetch
    for index, table in enumerate(to_fetch_now):
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
