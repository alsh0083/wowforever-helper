"""Combat-log summaries from foreverlogs.gg (#69), read from a HAR file the owner saved while browsing.

foreverlogs.gg's robots.txt disallows /api/ and /reports/ for crawlers, so this module never fetches
anything: it only reads API responses already in a browser HAR export (DevTools > Network > "Save
all as HAR"). Raw HARs stay out of git (data/cache/logs/); the summary keeps class, spec and
per-ability numbers and drops character names.

DPS is total damage over the summed wall time of the encounters the page asked for, so it is a
rough group-content number (downtime and pulls included), not a parse.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

SOURCE = "foreverlogs.gg"


def _seconds(start: str, end: str) -> float:
    parse = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    return (parse(end) - parse(start)).total_seconds()


def _responses(har: dict[str, Any]) -> Iterable[tuple[str, Any]]:
    for entry in har["log"]["entries"]:
        url = entry["request"]["url"]
        text = entry["response"]["content"].get("text")
        if "foreverlogs.gg/api/" in url and text:
            try:
                yield url, json.loads(text)
            except json.JSONDecodeError:
                continue


def _encounter_ids(url: str) -> tuple[str, ...]:
    query = parse_qs(urlparse(url).query)
    ids = query.get("encounterIds[]") or [i for v in query.get("encounterIds", []) for i in v.split(",")]
    return tuple(sorted(i for i in ids if i))


def summarize_har(har: dict[str, Any]) -> list[dict[str, Any]]:
    """One entry per (report, encounter set) with per-player ability damage, names dropped."""
    reports: dict[str, dict[str, Any]] = {}
    damage: list[tuple[str, tuple[str, ...], dict[str, Any]]] = []
    for url, body in _responses(har):
        if m := re.search(r"/api/reports/(\d+)$", urlparse(url).path):
            reports[m.group(1)] = body
        elif "/character_spell_damage" in url and parse_qs(urlparse(url).query).get("format") == ["by_source"]:
            damage.append((re.search(r"/reports/(\d+)/", url).group(1), _encounter_ids(url), body))

    out, seen = [], set()
    for report_id, ids, body in damage:
        if (report_id, ids) in seen or report_id not in reports:
            continue
        seen.add((report_id, ids))
        meta = reports[report_id]
        encounters = {str(e["id"]): e for e in meta["encounters"]}
        picked = [encounters[i] for i in ids if i in encounters]
        seconds = sum(_seconds(e["start_time"], e["end_time"]) for e in picked)
        if seconds <= 0:
            continue
        players = []
        for rows in body.get("spell_damage_by_source", {}).values():
            if not rows or rows[0].get("character_type") != "player":
                continue
            total = sum(float(r["total_damage"]) for r in rows)
            if total <= 0:
                continue
            players.append({
                "class": rows[0]["character_class"], "spec": rows[0].get("character_spec"),
                "damage": round(total), "dps": round(total / seconds, 1),
                "abilities": [{
                    "spell": r["spell_name"], "spell_id": int(r["spell_id"]),
                    "share": round(float(r["total_damage"]) / total, 3),
                    "casts": int(r["casts"] or 0), "hits": int(r["hits"] or 0),
                    "crit_pct": round(100 * int(r["crits"] or 0) / max(1, int(r["hits"] or 0)), 1),
                } for r in sorted(rows, key=lambda r: -float(r["total_damage"]))],
            })
        out.append({
            "source": SOURCE, "report": int(report_id), "title": meta["report"]["title"],
            "date": meta["report"]["start_time"][:10],
            "encounters": sorted({e["name"] for e in picked}), "kills": sum(bool(e["success"]) for e in picked),
            "seconds": round(seconds), "players": sorted(players, key=lambda p: (p["class"], str(p["spec"]))),
        })
    return out


def merge(existing: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add `new` summaries, replacing any with the same report and encounter set."""
    key = lambda s: (s["report"], tuple(s["encounters"]), s["seconds"])  # noqa: E731
    by_key = {key(s): s for s in existing}
    by_key.update({key(s): s for s in new})
    return sorted(by_key.values(), key=lambda s: (s["report"], s["seconds"]))


def import_hars(paths: Iterable[Path], out: Path) -> list[dict[str, Any]]:
    """Summarize each HAR and merge into `out` (JSON list)."""
    existing = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    new = [s for p in paths for s in summarize_har(json.loads(Path(p).read_text(encoding="utf-8")))]
    merged = merge(existing, new)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, indent=1), encoding="utf-8", newline="\n")
    return merged
