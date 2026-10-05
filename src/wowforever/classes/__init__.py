"""Per-class knowledge (trait-tree layout, school interactions, effect tagging).

Everything outside this package is class-agnostic.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Match



@dataclass(frozen=True)
class TreeBand:
    """One talent tree inside a class's trait tree: nodes with PosX >= min_x (up to the next band)."""

    tree_id: int
    name: str
    min_x: int


@dataclass(frozen=True)
class TraitLayout:
    """How to cut a class's trait tree into Classic-style trees, rows and columns."""

    class_name: str
    trait_tree_id: int
    trees: tuple[TreeBand, ...]  # ordered by min_x
    first_row_y: int             # PosY of row 0
    grid: int                    # PosX/PosY distance between adjacent rows/columns


@dataclass(frozen=True)
class EffectRule:
    """One numeric effect to parse out of a talent's rank text (#51)."""

    kind: str
    pattern: str                 # regex with one capture group for the number
    applies_to: tuple[str, ...]  # school names, spell names, "all", or "@condition" tokens
    sign: int = 1                # -1 for reductions (cast time, mana cost)
    combine: Callable[[Match[str]], float] | None = None  # several numbers, e.g. % x stacks


# Registered classes: name (also the wowforevertalent.com page slug) -> module with LAYOUT,
# TALENT_EFFECTS, UNMODELED and SKILL_LINES. Add a class here once its module exists.
CLASSES: dict[str, str] = {
    "mage": "wowforever.classes.mage",
    "rogue": "wowforever.classes.rogue",
}


def class_module(name: str):
    """The per-class module registered under `name`; KeyError for an unknown class."""
    import importlib

    return importlib.import_module(CLASSES[name])
