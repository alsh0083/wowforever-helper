"""Refresh the cached Forever Logs statistics (#172): re-fetch the /statistics endpoint per location.

`validate-logs` and `group-buffs` read four variant folders from data/cache/foreverlogs/, one JSON
response per location; they were fetched by hand. This module re-fetches them as one command. The
owner's key is sent only in the Authorization header, never in a URL, and never written to disk.
"""

from __future__ import annotations

import json
import re
import time
import tomllib
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from urllib.parse import urlencode

BASE = "https://foreverlogs.gg/api/public/v1"

VARIANTS: dict[str, dict[str, str]] = {
    "stats": {"metric": "avg_dps", "role": "dps"},
    "stats-boss-only": {"metric": "avg_dps", "role": "dps", "damageMode": "boss-only"},
    "stats-hps": {"metric": "avg_hps"},
    "stats-role-tank": {"metric": "avg_dps", "role": "tank"},
}

# Per-boss boss-only DPS for the bosses in config/single_target_bosses.toml (#249); one request per boss,
# so it is never part of the default refresh.
PER_BOSS = "stats-per-boss"


def cache_name(location: str) -> str:
    """Cache file name for a location: letters, digits and `-` are kept, everything else becomes `_`."""
    return re.sub(r"[^0-9A-Za-z-]", "_", location)


def statistics_url(location: str, params: dict[str, str]) -> str:
    """Statistics endpoint for one location: phase 1, all difficulties, the variant's params."""
    query = {"phase": "1", "difficulty": "all", **params, "location": location}
    return f"{BASE}/statistics?{urlencode(query)}"


def boss_statistics_url(location: str, boss_id: int) -> str:
    """Boss-only DPS statistics for one boss (Forever Logs `boss_id`) in its location."""
    return statistics_url(location, {**VARIANTS["stats-boss-only"], "bossId": str(boss_id)})


def fetch_statistics(
    cache_dir: Path,
    api_key: str,
    *,
    variants: Sequence[str],
    locations: Sequence[str],
    get: Callable[[str, dict[str, str]], str],
    sleep: Callable[[float], None] = time.sleep,
    delay: float = 2.0,
) -> list[Path]:
    """Re-fetch the statistics for every variant and location and write them under `cache_dir`."""
    for name in variants:
        if name not in VARIANTS:
            raise ValueError(f"unknown variant {name!r}; known: {', '.join(VARIANTS)}")
    headers = {"Authorization": f"Bearer {api_key}"}
    written: list[Path] = []
    for variant in variants:
        folder = cache_dir / variant
        folder.mkdir(parents=True, exist_ok=True)
        for location in locations:
            if written:
                sleep(delay)
            text = get(statistics_url(location, VARIANTS[variant]), headers)
            if json.loads(text).get("success") is not True:
                raise ValueError(f"statistics failed for {location} ({variant})")
            path = folder / f"{cache_name(location)}.json"
            path.write_text(text, encoding="utf-8", newline="\n")
            written.append(path)
    return written


def fetch_boss_statistics(
    cache_dir: Path,
    api_key: str,
    *,
    bosses: Sequence[tuple[str, int]],
    get: Callable[[str, dict[str, str]], str],
    sleep: Callable[[float], None] = time.sleep,
    delay: float = 2.0,
) -> list[Path]:
    """Fetch each (location, boss_id)'s boss-only statistics into `cache_dir`/stats-per-boss/<boss_id>.json."""
    headers = {"Authorization": f"Bearer {api_key}"}
    folder = cache_dir / PER_BOSS
    folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for location, boss_id in bosses:
        if written:
            sleep(delay)
        text = get(boss_statistics_url(location, boss_id), headers)
        if json.loads(text).get("success") is not True:
            raise ValueError(f"statistics failed for boss {boss_id} ({location})")
        path = folder / f"{boss_id}.json"
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def read_boss_list(path: Path) -> list[tuple[str, int]]:
    """(location, boss_id) for each boss in config/single_target_bosses.toml, in file order."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return [(b["location"], b["id"]) for b in data.get("bosses", [])]


def read_api_key(environ: Mapping[str, str], dotenv: Path) -> str:
    """The owner's key: FOREVERLOGS_API_KEY in the environment, then the .env file. Never printed."""
    value = environ.get("FOREVERLOGS_API_KEY", "").strip()
    if value:
        return value
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line.startswith("FOREVERLOGS_API_KEY="):
                continue
            value = line.partition("=")[2].strip()
            if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
                value = value[1:-1]
            if value:
                return value
    raise ValueError("set FOREVERLOGS_API_KEY in the environment or the .env file (the owner's key)")
