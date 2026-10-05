"""Normalize wago.tools trait tables and a wowforevertalent.com page into ClassData.

The client's Trait tables provide the structure (grid positions, max ranks,
prerequisites); the class page provides rank text, classic status, and icons.
What the two sources disagree about is recorded in a `NormalizeReport`
rather than dropped.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wowforever.classes import TraitLayout, TreeBand
from wowforever.schema import CLASSIC_STATUS, ClassData, Prerequisite, Rules, Talent, Tree
from wowforever.sources.wowforevertalent import WftPage

Tables = dict[str, list[dict[str, str]]]


def read_tables(directory: Path) -> Tables:
    """Read every *.csv in `directory` (UTF-8), keyed by file stem, rows as string dicts."""
    tables: Tables = {}
    for path in sorted(directory.glob("*.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            tables[path.stem] = list(csv.DictReader(handle))
    return tables


@dataclass
class NormalizeReport:
    """What normalize_class could not reconcile between the two sources."""

    build_mismatch: str | None = None
    unmatched_wago: list[str] = field(default_factory=list)  # wago talents with no page talent
    unmatched_wft: list[str] = field(default_factory=list)   # page talents with no wago talent
    name_mismatches: list[str] = field(default_factory=list)  # same position, different names
    ignored_edges: list[str] = field(default_factory=list)    # client edges that point upward

    @property
    def ok(self) -> bool:
        """True when no mismatch is flagged anywhere."""
        return (self.build_mismatch is None
                and not self.unmatched_wago
                and not self.unmatched_wft
                and not self.name_mismatches)


def _band_for(layout: TraitLayout, pos_x: int) -> TreeBand | None:
    """The band with the largest min_x not exceeding `pos_x`."""
    candidates = [band for band in layout.trees if band.min_x <= pos_x]
    if not candidates:
        return None
    return max(candidates, key=lambda band: band.min_x)


def _entry_details(node_id: str, tables: Tables) -> tuple[str, int, int]:
    """(name, max_rank, spell_id) of a node's single entry; choice nodes raise."""
    entry_ids = [row["TraitNodeEntryID"] for row in tables["TraitNodeXTraitNodeEntry"]
                 if row["TraitNodeID"] == node_id]
    if len(entry_ids) > 1:
        raise ValueError(f"trait node {node_id} is a choice node ({len(entry_ids)} entries)")
    if not entry_ids:
        raise ValueError(f"trait node {node_id} has no entries")
    entry = next((row for row in tables["TraitNodeEntry"] if row["ID"] == entry_ids[0]), None)
    if entry is None:
        raise ValueError(f"trait node {node_id}: missing TraitNodeEntry {entry_ids[0]}")
    definition = next((row for row in tables["TraitDefinition"]
                       if row["ID"] == entry["TraitDefinitionID"]), None)
    if definition is None:
        raise ValueError(f"trait node {node_id}: missing TraitDefinition {entry['TraitDefinitionID']}")
    spell_id = int(definition["SpellID"])
    name = next((row["Name_lang"] for row in tables["SpellName"] if row["ID"] == str(spell_id)), None)
    if name is None:
        raise ValueError(f"trait node {node_id}: no SpellName for spell {spell_id}")
    return name, int(entry["MaxRanks"]), spell_id


def _snapped(pos: int, origin: int, layout: TraitLayout) -> int:
    """`pos` moved onto the nearest grid line from `origin` when within `layout.snap` of it."""
    offset = (pos - origin) % layout.grid
    if offset <= layout.snap:
        return pos - offset
    if layout.grid - offset <= layout.snap:
        return pos + layout.grid - offset
    return pos


def normalize_class(tables: Tables, layout: TraitLayout, page: WftPage, *,
                    wago_build: str) -> tuple[ClassData, NormalizeReport]:
    """Cut `layout`'s trait tree into Classic-style trees and join it with `page`."""
    report = NormalizeReport()
    if page.game_build != wago_build:
        report.build_mismatch = (
            f"source builds disagree: wago tables are build {wago_build}, "
            f"wowforevertalent.com page is build {page.game_build}"
        )

    band_index = {band.tree_id: position for position, band in enumerate(layout.trees)}
    band_name = {band.tree_id: band.name for band in layout.trees}

    @dataclass
    class _Placed:
        talent_id: int
        tree_id: int
        row: int
        col: int
        name: str
        max_rank: int
        spell_id: int

    placed: list[_Placed] = []
    for row in tables["TraitNode"]:
        if row["TraitTreeID"] != str(layout.trait_tree_id):
            continue
        node_id = int(row["ID"])
        if node_id in layout.hidden_nodes:
            continue
        pos_x, pos_y = int(row["PosX"]), int(row["PosY"])
        band = _band_for(layout, pos_x + layout.snap)
        if band is None:
            raise ValueError(f"trait node {node_id}: PosX {pos_x} is left of every tree band")
        pos_x = _snapped(pos_x, band.min_x, layout)
        pos_y = _snapped(pos_y, layout.first_row_y, layout)
        if (pos_x - band.min_x) % layout.grid or (pos_y - layout.first_row_y) % layout.grid:
            raise ValueError(f"trait node {node_id}: position ({pos_x}, {pos_y}) is off the grid")
        name, max_rank, spell_id = _entry_details(row["ID"], tables)
        placed.append(_Placed(node_id, band.tree_id,
                              (pos_y - layout.first_row_y) // layout.grid,
                              (pos_x - band.min_x) // layout.grid,
                              name, max_rank, spell_id))

    # Edges: the right node requires the left node at the left node's max rank.
    max_rank_by_id = {p.talent_id: p.max_rank for p in placed}
    by_id = {p.talent_id: p for p in placed}
    prerequisites: dict[int, Prerequisite] = {}
    for edge in tables["TraitEdge"]:
        left_id, right_id = int(edge["LeftTraitNodeID"]), int(edge["RightTraitNodeID"])
        if left_id not in max_rank_by_id or right_id not in max_rank_by_id:
            continue
        if by_id[left_id].row >= by_id[right_id].row:
            # a prerequisite always sits above what it unlocks; e.g. the hunter tree also has
            # Bestial Wrath -> Intimidation besides the real Intimidation -> Bestial Wrath
            report.ignored_edges.append(f"{by_id[left_id].name} -> {by_id[right_id].name}")
            continue
        if right_id in prerequisites:
            raise ValueError(f"trait node {right_id}: multiple prerequisite edges")
        prerequisites[right_id] = Prerequisite(left_id, max_rank_by_id[left_id])

    # Join with the page: its rows and columns are 1-indexed, ours 0-indexed.
    page_tree_index = {tree["name"]: position for position, tree in enumerate(page.trees)}
    page_talent_at: dict[tuple[int, int, int], dict[str, Any]] = {}
    for tree_position, tree in enumerate(page.trees):
        for talent in tree["talents"]:
            page_talent_at[(tree_position, int(talent["row"]), int(talent["col"]))] = talent
    matched: set[tuple[int, int, int]] = set()

    ordered = sorted(placed, key=lambda p: (band_index[p.tree_id], p.row, p.col))
    talents: list[Talent] = []
    for p in ordered:
        page_talent = None
        matched_key = None
        tree_position = page_tree_index.get(band_name[p.tree_id])
        if tree_position is not None:
            matched_key = (tree_position, p.row + 1, p.col + 1)
            page_talent = page_talent_at.get(matched_key)
        rank_text: tuple[str, ...] = ()
        classic_status: str | None = None
        icon = ""
        if page_talent is None:
            report.unmatched_wago.append(f"{band_name[p.tree_id]}/{p.name}")
        else:
            matched.add(matched_key)
            if str(page_talent["name"]).lower() != p.name.lower():
                report.name_mismatches.append(
                    f"{band_name[p.tree_id]}/{p.name}: wowforevertalent.com has {page_talent['name']}")
            else:
                rank_text = tuple(rank["text"] for rank in
                                  sorted(page_talent["ranks"], key=lambda rank: rank["rank"]))
                classic = page_talent.get("classic")
                status = classic.get("status") if isinstance(classic, dict) else None
                classic_status = status if status in CLASSIC_STATUS else None
                icon = page_talent.get("icon") or ""
        talents.append(Talent(
            talent_id=p.talent_id, name=p.name, tree_id=p.tree_id, row=p.row, col=p.col,
            max_rank=p.max_rank, rank_spell_ids=(), rank_text=rank_text,
            prerequisite=prerequisites.get(p.talent_id), classic_status=classic_status,
            icon=icon, spell_id=p.spell_id,
        ))

    for tree_position, tree in enumerate(page.trees):
        for talent in tree["talents"]:
            key = (tree_position, int(talent["row"]), int(talent["col"]))
            if key not in matched:
                report.unmatched_wft.append(f"{tree['name']}/{talent['name']}")

    trees = tuple(
        Tree(band.tree_id, band.name, tuple(
            p.talent_id for p in ordered if p.tree_id == band.tree_id
        ))
        for band in layout.trees
    )
    return ClassData(layout.class_name, trees, tuple(talents), rules=Rules()), report
