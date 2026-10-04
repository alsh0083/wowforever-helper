"""Per-class knowledge (trait-tree layout, school interactions, effect tagging).

Everything outside this package is class-agnostic.
"""

from dataclasses import dataclass


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
