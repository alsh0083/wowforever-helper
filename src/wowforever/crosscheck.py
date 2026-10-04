"""Cross-source consistency check (#12): build lag and data disagreements between
the wago.tools tables and the wowforevertalent.com page for one class.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wowforever.normalize import NormalizeReport
from wowforever.schema import ClassData
from wowforever.sources.wowforevertalent import WftPage

WAGO = "wago.tools"
WFT = "wowforevertalent.com"


@dataclass
class CrosscheckResult:
    """Builds seen at each source, which one lags, and the disagreements found."""

    lagging_source: str | None
    builds: dict[str, str]
    problems: list[str]

    @property
    def ok(self) -> bool:
        """True when the builds agree and no disagreement was found."""
        return self.lagging_source is None and not self.problems

    def summary(self) -> str:
        """One line per finding; the build lag (when any) comes first."""
        if self.ok:
            return "Sources agree."
        lines: list[str] = []
        if self.lagging_source is not None:
            other = WAGO if self.lagging_source == WFT else WFT
            lines.append(f"{self.lagging_source} is on build {self.builds[self.lagging_source]}; "
                         f"{other} is on build {self.builds[other]}.")
        lines.extend(self.problems)
        return "\n".join(lines)


def _build_number(build: str) -> tuple[int, ...]:
    """A dotted build string as comparable ints, e.g. '1.60.1.70205'."""
    return tuple(int(part) for part in build.split("."))


def _page_positions(page: WftPage) -> dict[tuple[int, int, int], dict[str, Any]]:
    """(tree index, 1-indexed row, 1-indexed col) -> page talent dict."""
    positions: dict[tuple[int, int, int], dict[str, Any]] = {}
    for tree_index, tree in enumerate(page.trees):
        for talent in tree["talents"]:
            positions[(tree_index, int(talent["row"]), int(talent["col"]))] = talent
    return positions


def _page_prerequisite_name(positions: dict[tuple[int, int, int], dict[str, Any]],
                            raw: Any) -> str | None:
    """Resolve a page talent id like '2-5-2' to that talent's name."""
    if not raw:
        return None
    try:
        key = tuple(int(part) for part in str(raw).split("-"))
    except ValueError:
        return str(raw)
    if len(key) != 3:
        return str(raw)
    talent = positions.get(key)
    return str(talent["name"]) if talent is not None else str(raw)


def crosscheck(cls: ClassData, page: WftPage, report: NormalizeReport, *,
               wago_build: str) -> CrosscheckResult:
    """Compare the wago-derived `cls` with the `page`, carrying over `report` problems."""
    builds = {WAGO: wago_build, WFT: page.game_build}
    wago_number, page_number = _build_number(wago_build), _build_number(page.game_build)
    if page_number < wago_number:
        lagging: str | None = WFT
    elif wago_number < page_number:
        lagging = WAGO
    else:
        lagging = None

    problems: list[str] = [*report.unmatched_wago, *report.unmatched_wft,
                           *report.name_mismatches]
    positions = _page_positions(page)
    tree_index_by_name = {tree["name"]: index for index, tree in enumerate(page.trees)}
    tree_name_by_id = {tree.tree_id: tree.name for tree in cls.trees}
    for talent in cls.talents:
        tree_index = tree_index_by_name.get(tree_name_by_id.get(talent.tree_id, ""))
        if tree_index is None:
            continue
        page_talent = positions.get((tree_index, talent.row + 1, talent.col + 1))
        if page_talent is None or str(page_talent["name"]).lower() != talent.name.lower():
            continue
        label = f"{tree_name_by_id[talent.tree_id]}/{talent.name}"
        page_max_rank = int(page_talent["maxRank"])
        if page_max_rank != talent.max_rank:
            problems.append(f"{label}: max rank {talent.max_rank} ({WAGO}) vs "
                            f"{page_max_rank} ({WFT})")
        if talent.prerequisite is not None:
            prereq = next((t for t in cls.talents
                           if t.talent_id == talent.prerequisite.talent_id), None)
            wago_name = prereq.name if prereq is not None else str(talent.prerequisite.talent_id)
        else:
            wago_name = None
        page_name = _page_prerequisite_name(positions, page_talent.get("prerequisite"))
        if wago_name != page_name:
            problems.append(f"{label}: prerequisite {wago_name or 'none'} ({WAGO}) vs "
                            f"{page_name or 'none'} ({WFT})")
    return CrosscheckResult(lagging, builds, problems)
