"""Refreshing hand-adjusted community builds from post-patch popularity data (#369)."""

from __future__ import annotations

import ast

from wowforever.melee_scenarios import main_tree


def closest_popular(build, cls, top) -> dict | None:
    """The post-patch popular build in `build`'s main tree that shares the most talent points with it (ties: the
    most saved), with its `final` limited to talents the class has and its `overlap`; None without one."""
    names = {t.name for t in cls.talents}
    tree = main_tree(cls, build.final_ids(cls))
    best = None
    for entry in top:
        final = {name: rank for name, rank in entry["final"].items() if name in names}
        if main_tree(cls, {cls.talent_named(n).talent_id: r for n, r in final.items()}) != tree:
            continue
        overlap = sum(min(rank, build.final.get(name, 0)) for name, rank in final.items())
        key = (overlap, int(entry["saved"]))
        if best is None or key > best[0]:
            best = (key, {**entry, "final": final, "overlap": overlap})
    return best[1] if best else None


PROVISIONAL_SAVES = 20     # fewer saves than this: the post-patch pick is provisional until the meta settles


def final_signature(final: dict) -> str:
    """The talents of a build as one comparable string, whatever their order."""
    return ",".join(f"{name}={rank}" for name, rank in sorted(final.items()) if rank > 0)


def refreshed_toml(text: str, entry: dict, *, window: str, today: str = "") -> str:
    """`text` (a build file) with the `adjusted` mark and its notes gone and `[final]` taken from `entry`, marked
    with the player build it came from and, on a thin sample, as provisional."""
    lines = [line for line in text.splitlines()
             if not line.startswith(("provisional =", "refreshed =", "# refreshed from"))]
    start = next((i for i, line in enumerate(lines) if line.startswith("adjusted =")), None)
    final_at = lines.index("[final]")
    if start is not None:
        del lines[start:final_at]
        final_at = start
    end = next((i for i in range(final_at + 1, len(lines)) if not lines[i].startswith('"')), len(lines))
    points = entry["points"] if isinstance(entry["points"], list) else ast.literal_eval(entry["points"])
    marks =[f'refreshed = "{entry["rank"]}:{final_signature(entry["final"])}"']
    if entry["saved"] < PROVISIONAL_SAVES:
        marks.append(f'provisional = "{entry["saved"]} saves, {today}"')
    note = (f"# refreshed from wowforevertalent.com popularity ({window}): rank {entry['rank']}, saved "
            f"{entry['saved']}, points {'/'.join(str(p) for p in points)} (#369)")
    body = [f'"{name}" = {rank}' for name, rank in entry["final"].items() if rank > 0]
    return "\n".join(lines[:final_at] + marks + [note, "[final]"] + body + lines[end:]) + "\n"


def refresh_status(build, entry: dict) -> str:
    """"moved" when the closest player build isn't the one `build` was refreshed from, else "settled" once it has
    PROVISIONAL_SAVES saves, else "stable"."""
    if not build.refreshed or build.refreshed.split(":", 1)[1] != final_signature(entry["final"]):
        return "moved"
    return "settled" if entry["saved"] >= PROVISIONAL_SAVES else "stable"
