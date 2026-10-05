"""In-game test checklist (#31): one item per unknown-mechanic assumption, so the owner
can test each in game, record the result, and retest the ones a patch change touches."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from wowforever.assumptions import Assumptions
from wowforever.revisions import Change


@dataclass(frozen=True)
class ChecklistItem:
    name: str          # assumption name
    question: str      # the assumption's `why`
    assumed: Any       # current value
    options: tuple[Any, ...]
    talents: tuple[str, ...]
    status: str        # "untested" | "tested" | "retest"
    result: str        # the `tested` text ("" when untested)


def checklist(assumptions: Assumptions, changes: Sequence[Change] = ()) -> list[ChecklistItem]:
    """One item per assumption, in config order.

    Untested assumptions stay "untested" even when a change touches them; a tested
    one becomes "retest" when some change names a talent or spell it involves
    (case-insensitive).
    """
    changed = {change.talent.lower() for change in changes}
    items = []
    for name, a in assumptions.entries.items():
        if not a.tested:
            status = "untested"
        elif any(talent.lower() in changed for talent in a.talents):
            status = "retest"
        else:
            status = "tested"
        items.append(ChecklistItem(name, a.why, a.value, a.options, a.talents, status, a.tested))
    return items


def retest_names(assumptions: Assumptions, changes: Sequence[Change] = ()) -> list[str]:
    """Names of the tested assumptions a patch change flags for a retest in game."""
    return [item.name for item in checklist(assumptions, changes) if item.status == "retest"]
