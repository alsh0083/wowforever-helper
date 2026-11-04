"""Community standards from current sources (#460; owner, 2026-10-31: "only have the standards that you can source").

Each slot (archetype x focus) takes, in order:
1. wowforeverbuilds.com's spec guide build for that focus, when `standard_build` keeps it;
2. talentsforever.com's most saved top build whose talents land in the slot (PvE only: the site doesn't say what a
   build is for);
3. nothing: the slot's model build holds it.
A build is taken as published. A talent our trees don't have, a rank over its cap, unspent points, or a build that
isn't legal at 60 drops it; nothing is adjusted.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from wowforever.rules import check_build, points_available
from wowforever.schema import ClassData
from wowforever.shortlist import classify


@dataclass(frozen=True)
class Sourced:
    archetype: str
    focus: str                     # "PvE" or "PvP"
    ranks: Mapping[str, int]       # talent name -> rank, as published
    source: str                    # "wowforeverbuilds.com" or "talentsforever.com"
    url: str
    title: str                     # the guide's title, or the site's build name
    note: str                      # where it ranks on the site


@dataclass(frozen=True)
class Candidate:
    focus: str | None              # None when the source doesn't say (talentsforever.com)
    ranks: Mapping[str, int]
    source: str
    url: str
    title: str
    note: str


def on_our_trees(ranks: Mapping[str, int], cls: ClassData) -> tuple[dict[int, int] | None, str]:
    """`ranks` by talent id when every talent is ours and within its cap, all points are spent and the build is legal
    at 60; otherwise (None, why)."""
    by_name = {t.name: t for t in cls.talents}
    for name, rank in ranks.items():
        talent = by_name.get(name)
        if talent is None:
            return None, f"{name}: not a talent on our trees"
        if rank > talent.max_rank:
            return None, f"{name}: rank {rank} is over its cap {talent.max_rank}"
    ids = {by_name[name].talent_id: rank for name, rank in ranks.items()}
    level = cls.rules.max_level
    spent, available = sum(ids.values()), points_available(level, cls.rules)
    if spent != available:
        return None, f"spends {spent} of {available} points"
    errors = check_build(cls, ids, level)
    return (None, "not legal: " + "; ".join(errors)) if errors else (ids, "")


def pick(cls: ClassData, guides: Sequence[Candidate], top: Sequence[Candidate], *, deep: int, hybrid: int,
         recognized: tuple[str, ...]) -> tuple[list[Sourced], list[str]]:
    """One community build per slot, guides first, then the top builds in the order given (most saved first).
    Returns the builds and a line for each candidate left out."""
    chosen: dict[tuple[str, str], Sourced] = {}
    skipped: list[str] = []
    for candidate in [*guides, *top]:
        ids, why = on_our_trees(candidate.ranks, cls)
        if ids is None:
            skipped.append(f"{candidate.title}: {why}")
            continue
        archetype = classify(cls, ids, deep=deep, hybrid=hybrid, recognized=recognized)
        if archetype is None:
            skipped.append(f"{candidate.title}: no archetype (points {_split(cls, ids)})")
            continue
        slot = (archetype, candidate.focus or "PvE")
        if slot in chosen:
            skipped.append(f"{candidate.title}: {archetype} {slot[1]} already has {chosen[slot].title}")
            continue
        chosen[slot] = Sourced(archetype, slot[1], dict(candidate.ranks), candidate.source, candidate.url,
                               candidate.title, candidate.note)
    return list(chosen.values()), skipped


def _split(cls: ClassData, ids: Mapping[int, int]) -> str:
    return "/".join(str(sum(ids.get(t, 0) for t in tree.talent_ids)) for tree in cls.trees)


SOURCE_KEYS = {"wowforeverbuilds.com": "wowforeverbuilds_guides", "talentsforever.com": "talentsforever_top"}


def build_toml(class_name: str, s: Sourced, captured: str) -> tuple[str, str]:
    """(build id, file text) for config/builds/: the build as published, labelled with where it came from."""
    tree = s.archetype.removeprefix("deep ")
    pair = f"{class_name}-" + tree.lower().replace("/", "-").replace(" ", "-")
    build_id = pair + ("-pvp" if s.focus == "PvP" else "")
    credit = " Data (c) Talents Forever, https://talentsforever.com, CC BY 4.0." if s.source == "talentsforever.com" else ""
    lines = [f"# Community standard (#460) from {s.source}, saved {captured}: {s.note}.{credit}",
             f"# {s.url}",
             "# Taken as published: tools/import_sourced_builds.py replaces it, never adjusts it.", "",
             f'id = "{build_id}"', f'class = "{class_name}"', f"name = {json.dumps(f'{tree} ({s.focus})')}",
             f'pair = "{pair}"', f'variant = "{s.focus}"', 'origin = "community"', f'sources = ["{SOURCE_KEYS[s.source]}"]',
             'confidence = "medium"', f"summary = {json.dumps(f'{s.title} ({s.source}, {s.note}).')}", "", "[final]"]
    lines += [f"{json.dumps(name)} = {rank}" for name, rank in sorted(s.ranks.items())]
    return build_id, "\n".join(lines) + "\n"
