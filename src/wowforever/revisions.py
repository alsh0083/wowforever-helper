"""Revision tracking (#11): talent/spell diffs between data snapshots, the
Markdown changelog, the update-check registry, and affected builds.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, fields
from pathlib import Path

from wowforever.builds import Build
from wowforever.schema import ClassData, Prerequisite, SpellRank, Talent

_CHANGELOG_HEADER = "# Data changelog\n"
_NO_CHANGES = "- No talent or spell changes."
_RENAMED_PREFIX = "renamed to "
_SPELL_DIFF_FIELDS = tuple(
    f for f in fields(SpellRank) if f.name not in ("spell_id", "name", "rank")
)


@dataclass(frozen=True)
class Change:
    """One talent or spell difference between two snapshots.

    `talent` is the name before the change; spells use `scope == ""` and carry
    their rank in `rank`.
    """

    scope: str
    talent: str
    kind: str
    text: str
    rank: int = 0

    def __str__(self) -> str:
        if self.scope:
            return f"{self.scope}/{self.talent}: {self.text}"
        return f"{self.talent} rank {self.rank}: {self.text}"


def _scope_by_id(class_data: ClassData) -> dict[int, str]:
    """talent_id -> tree name for the `{scope}/{talent}` labels."""
    return {talent_id: tree.name for tree in class_data.trees for talent_id in tree.talent_ids}


def _prereq_text(prereq: Prerequisite | None, by_id: dict[int, Talent]) -> str:
    """`{name} (rank {n})` for a prerequisite, or `none`."""
    if prereq is None:
        return "none"
    name = by_id.get(prereq.talent_id)
    label = name.name if name is not None else str(prereq.talent_id)
    return f"{label} (rank {prereq.rank})"


def diff_class(old: ClassData, new: ClassData) -> list[Change]:
    """Talent changes between two snapshots of a class, matched by talent_id."""
    old_by_id = {t.talent_id: t for t in old.talents}
    new_by_id = {t.talent_id: t for t in new.talents}
    old_scope, new_scope = _scope_by_id(old), _scope_by_id(new)
    changes: list[Change] = []
    for talent_id, before in old_by_id.items():
        after = new_by_id.get(talent_id)
        if after is None:
            changes.append(Change(old_scope[talent_id], before.name, "removed", "removed"))
            continue
        scope = old_scope[talent_id]
        if after.name != before.name:
            changes.append(Change(scope, before.name, "changed", f"renamed to {after.name}"))
        if after.max_rank != before.max_rank:
            changes.append(Change(scope, before.name, "changed",
                                  f"max rank {before.max_rank} -> {after.max_rank}"))
        if (after.tree_id, after.row, after.col) != (before.tree_id, before.row, before.col):
            changes.append(Change(scope, before.name, "changed",
                                  f"moved from row {before.row + 1} col {before.col + 1}"
                                  f" to row {after.row + 1} col {after.col + 1}"))
        if before.prerequisite != after.prerequisite:
            changes.append(Change(scope, before.name, "changed",
                                  f"prerequisite {_prereq_text(before.prerequisite, old_by_id)}"
                                  f" -> {_prereq_text(after.prerequisite, new_by_id)}"))
        if before.rank_text != after.rank_text:
            changes.append(Change(scope, before.name, "changed", "rank text changed"))
    for talent_id, after in new_by_id.items():
        if talent_id not in old_by_id:
            changes.append(Change(new_scope[talent_id], after.name, "added", "new talent"))
    return changes


def diff_spells(old: Sequence[SpellRank], new: Sequence[SpellRank]) -> list[Change]:
    """Spell-rank changes between two snapshots, matched by spell_id."""
    old_ids = {spell.spell_id for spell in old}
    changes: list[Change] = []
    for before in old:
        after = next((s for s in new if s.spell_id == before.spell_id), None)
        if after is None:
            changes.append(Change("", before.name, "removed", "removed", before.rank))
            continue
        for field in _SPELL_DIFF_FIELDS:
            old_value, new_value = getattr(before, field.name), getattr(after, field.name)
            if old_value != new_value:
                changes.append(Change("", before.name, "changed",
                                      f"{field.name} {old_value} -> {new_value}", before.rank))
    for after in new:
        if after.spell_id not in old_ids:
            changes.append(Change("", after.name, "added", "new spell rank", after.rank))
    return changes


def affected_builds(changes: Sequence[Change], builds: Sequence[Build]) -> list[str]:
    """Ids of builds that name a changed talent (renames match old and new names)."""
    names = set()
    for change in changes:
        names.add(change.talent.lower())
        if change.text.startswith(_RENAMED_PREFIX):
            names.add(change.text[len(_RENAMED_PREFIX):].lower())
    affected = []
    for build in builds:
        used = set(build.final) | set(build.must_have_by) | set(build.order or ())
        if any(name.lower() in names for name in used):
            affected.append(build.id)
    return affected


@dataclass
class _Section:
    """One changelog section: `## <build> (<date>)`, an optional hand-written note, its items."""

    heading: str
    note: tuple[str, ...]
    items: list[str]


def _parse_changelog(text: str, source: object) -> list[_Section]:
    if text and not text.startswith(_CHANGELOG_HEADER):
        raise ValueError(f"{source} is not a data changelog")
    sections: list[_Section] = []
    for line in text[len(_CHANGELOG_HEADER):].splitlines():
        if line.startswith("## "):
            sections.append(_Section(line, (), []))
        elif line.startswith("- ") and sections:
            sections[-1].items.append(line)
        elif line and sections:                     # note paragraph (`> ` lines)
            sections[-1].note += (line,)
        elif line:
            raise ValueError(f"{source}: text before the first section: {line!r}")
    return sections


def _merged_items(*groups: Sequence[str]) -> list[str]:
    """Sorted, unique items; the no-changes line only when there's nothing else."""
    items = sorted({item for group in groups for item in group} - {_NO_CHANGES})
    return items or [_NO_CHANGES]


def _render_changelog(sections: Sequence[_Section]) -> str:
    out = [_CHANGELOG_HEADER]
    for section in sections:
        out.append(f"\n{section.heading}\n\n")
        if section.note:
            out.append("".join(f"{line}\n" for line in section.note) + "\n")
        out.append("".join(f"{item}\n" for item in section.items))
    return "".join(out)


def append_changelog(path: Path | str, build: str, changes: Sequence[Change], *,
                     date: str) -> None:
    """Insert a newest-first dated section for `build` into the changelog at `path`. Each class
    of one update check lands in the same section (#241), unless that section carries a note."""
    path = Path(path)
    sections = _parse_changelog(path.read_text(encoding="utf-8") if path.exists() else "", path)
    heading = f"## {build} ({date})"
    new = [f"- {change}" for change in changes]
    if sections and sections[0].heading == heading and not sections[0].note:
        sections[0].items = _merged_items(sections[0].items, new)
    else:
        sections.insert(0, _Section(heading, (), _merged_items(new)))
    path.write_text(_render_changelog(sections), encoding="utf-8", newline="\n")


def collapse_changelog(text: str) -> str:
    """Merge sections with the same heading and note into the first of them (#241)."""
    merged: dict[tuple[str, tuple[str, ...]], _Section] = {}
    for section in _parse_changelog(text, "text"):
        key = (section.heading, section.note)
        if key in merged:
            merged[key].items = _merged_items(merged[key].items, section.items)
        else:
            merged[key] = _Section(section.heading, section.note, _merged_items(section.items))
    return _render_changelog(list(merged.values()))


def record_check(path: Path | str, build: str, *, changed: bool, dataset: str | None,
                 checked_at: str) -> None:
    """Record an update check in the JSON registry at `path`; one entry per build."""
    path = Path(path)
    entries = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    entry = {"build": build, "changed": changed, "dataset": dataset, "checked_at": checked_at}
    for index, existing in enumerate(entries):
        if existing["build"] == build:
            if existing["checked_at"] == checked_at:   # another class in the same run
                entry["changed"] = existing["changed"] or changed
                entry["dataset"] = dataset or existing["dataset"]
            entries[index] = entry
            break
    else:
        entries.append(entry)
    path.write_text(json.dumps(entries, indent=1), encoding="utf-8", newline="\n")
