"""Fetcher for wago.tools DB2 table CSVs.

wago.tools serves raw DB2 table CSVs per game build (db2/<Table>/csv?build=...). The cache
under cache_dir is disposable (any file can be re-downloaded using the manifest hashes);
the manifest under manifest_dir is the record of what was fetched and when.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from wowforever.sources.http import http_get as default_http_get

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


def fetch_build(
    build: str,
    *,
    http_get: Callable[[str], str] | None = None,
    cache_dir: Path,
    manifest_dir: Path,
    tables: Sequence[str] = TABLES,
    delay: float = 1.0,
) -> Path:
    """Download `tables` for `build` into the cache, keeping a manifest record.

    A table whose cached file exists and matches the manifest hash is skipped (no HTTP
    call). A missing cache file is refetched; a refetch whose hash no longer matches the
    manifest raises `ValueError` (data changed under the same build).
    """
    if http_get is None:
        http_get = default_http_get
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
    for index, table in enumerate(to_fetch):
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
