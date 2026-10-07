"""Model vs Forever Logs (#172): average DPS per class and spec from the public statistics API,
next to the model's dungeon score at the nearest checkpoint for the builds of that spec.

Statistics are cached by hand from foreverlogs.gg's public API (`/api/public/v1/statistics`, owner's
key; data/cache/foreverlogs/stats/, and `damageMode=boss-only` in stats-boss-only/; not committed). Parses are bucketed by each dungeon's typical
level (config/log_levels.toml). A spec maps to the scored builds whose main tree has its name.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1].parent
LEVELS = ROOT / "config" / "log_levels.toml"
STATS_DIR = ROOT / "data" / "cache" / "foreverlogs" / "stats"
CHECKPOINTS = (20, 30, 40, 50, 60)


def log_averages(stats_dir: Path = STATS_DIR, levels_path: Path = LEVELS) -> dict[tuple[str, str, int], tuple[float, int]]:
    """(class, spec, checkpoint) -> (parse-weighted average DPS, parses)."""
    levels = tomllib.loads(levels_path.read_text(encoding="utf-8"))
    sums: dict[tuple[str, str, int], list[float]] = {}
    for path in sorted(stats_dir.glob("*.json")):
        body = json.loads(path.read_text(encoding="utf-8"))
        level = levels.get(body.get("location", ""))
        if level is None:
            continue
        checkpoint = min(CHECKPOINTS, key=lambda c: abs(c - level))
        for cls, data in (body.get("statistics") or {}).items():
            for spec, s in data["specs"].items():
                acc = sums.setdefault((cls.lower(), spec, checkpoint), [0.0, 0])
                acc[0] += s["avg"] * s["total_parses"]
                acc[1] += s["total_parses"]
    return {k: (total / n, int(n)) for k, (total, n) in sums.items() if n}


def log_percentiles(stats_dir: Path = STATS_DIR, levels_path: Path = LEVELS,
                    keys: tuple[str, ...] = ("p75", "p90")) -> dict[tuple[str, str, int], dict[str, float]]:
    """(class, spec, checkpoint) -> parse-weighted mean of each dungeon's percentile DPS. The model plays
    an optimized build without mistakes, so the stronger parses are the fairer comparison; the
    average includes undergeared and learning players."""
    levels = tomllib.loads(levels_path.read_text(encoding="utf-8"))
    sums: dict[tuple[str, str, int], dict[str, list[float]]] = {}
    for path in sorted(stats_dir.glob("*.json")):
        body = json.loads(path.read_text(encoding="utf-8"))
        level = levels.get(body.get("location", ""))
        if level is None:
            continue
        checkpoint = min(CHECKPOINTS, key=lambda c: abs(c - level))
        for cls, data in (body.get("statistics") or {}).items():
            for spec, s in data["specs"].items():
                pct = s.get("percentiles") or {}
                for k in keys:
                    if k in pct:
                        acc = sums.setdefault((cls.lower(), spec, checkpoint), {}).setdefault(k, [0.0, 0])
                        acc[0] += pct[k] * s["total_parses"]
                        acc[1] += s["total_parses"]
    return {key: {k: total / n for k, (total, n) in by.items() if n} for key, by in sums.items()}


def model_scores(report: dict[str, Any]) -> dict[tuple[str, int], list[float]]:
    """(main tree, checkpoint) -> the dungeon scores of the report's scored builds."""
    trees = {int(tid): t["tree"] for tid, t in report["talents"].items()}
    out: dict[tuple[str, int], list[float]] = {}
    for build in report["builds"]:
        dungeon = (build.get("scores") or {}).get("dungeon") or {}
        if not dungeon:
            continue
        points: dict[str, int] = {}
        for tid in build["order"]:
            points[trees[int(tid)]] = points.get(trees[int(tid)], 0) + 1
        tree = max(points, key=points.get)
        for level, cell in dungeon.items():
            if cell and cell.get("score") is not None:
                out.setdefault((tree, int(level)), []).append(cell["score"])
    return out


def compare(reports: Iterable[dict[str, Any]], logs: dict[tuple[str, str, int], tuple[float, int]],
            percentiles: dict[tuple[str, str, int], dict[str, float]] | None = None) -> list[dict[str, Any]]:
    """One row per logged (class, spec, checkpoint) that the model scores; with `percentiles`, also the
    model against the p75 and p90 parses."""
    models = {r.get("class", "mage"): model_scores(r) for r in reports}
    rows = []
    for (cls, spec, level), (avg, parses) in sorted(logs.items()):
        scores = models.get(cls, {}).get((spec, level))
        if not scores:
            continue
        mid = (min(scores) + max(scores)) / 2
        row = {"class": cls, "spec": spec, "level": level, "log_dps": round(avg, 1), "parses": parses,
               "model_min": round(min(scores), 1), "model_max": round(max(scores), 1),
               "ratio": round(mid / avg, 2) if avg else None}
        for k, v in ((percentiles or {}).get((cls, spec, level)) or {}).items():
            row[f"{k}_dps"], row[f"ratio_{k}"] = round(v, 1), round(mid / v, 2) if v else None
        rows.append(row)
    return rows


def markdown(rows: list[dict[str, Any]]) -> str:
    pct = any("p90_dps" in r for r in rows)
    lines = ["| Class | Spec | Level | Logs (parses) | Model | Model / logs |" + (" p75 | Model / p75 | p90 | Model / p90 |" if pct else ""),
             "|---|---|---|---|---|---|" + ("---|---|---|---|" if pct else "")]
    for r in rows:
        model = f"{r['model_min']:.0f}" if r["model_min"] == r["model_max"] else f"{r['model_min']:.0f}-{r['model_max']:.0f}"
        extra = "".join(f" {r[f'{k}_dps']:.0f} | {r[f'ratio_{k}']:.2f} |" if f"{k}_dps" in r else " – | – |"
                        for k in ("p75", "p90")) if pct else ""
        lines.append(f"| {r['class'].title()} | {r['spec']} | {r['level']} | {r['log_dps']:.0f} ({r['parses']}) "
                     f"| {model} | {r['ratio']:.2f} |{extra}")
    return "\n".join(lines)
