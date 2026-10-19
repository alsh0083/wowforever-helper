"""Per-class knowledge (trait-tree layout, school interactions, effect tagging).

Everything outside this package is class-agnostic.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Match, Protocol

if TYPE_CHECKING:
    from wowforever.melee_scenarios import Output
    from wowforever.physical import Target
    from wowforever.schema import ClassData, SpellRank



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
    # Trait nodes left in the client but not in the game's talent UI: Forever parks replaced
    # Classic nodes far off the grid. Skipped; each id is explained in the class module.
    hidden_nodes: frozenset[int] = frozenset()
    # Positions within `snap` units of a grid point round to it: Forever nudged a few nodes
    # 10 units off (paladin, warlock). 0 means exact.
    snap: int = 0


@dataclass(frozen=True)
class EffectRule:
    """One numeric effect to parse out of a talent's rank text (#51)."""

    kind: str
    pattern: str                 # regex with one capture group for the number
    applies_to: tuple[str, ...]  # school names, spell names, "all", or "@condition" tokens
    sign: int = 1                # -1 for reductions (cast time, mana cost)
    combine: Callable[[Match[str]], float] | None = None  # several numbers, e.g. % x stacks


def below_health(match: Match[str]) -> float:
    """A bonus that holds below a health threshold, averaged over the fight (#392): with steady damage the target
    spends N% of the fight below N% health, so the bonus counts at bonus x N / 100. The two captured numbers
    multiply, so their order in the rank text doesn't matter."""
    return float(match.group(1)) * float(match.group(2)) / 100


# Registered classes: name (also the wowforevertalent.com page slug) -> module with LAYOUT,
# TALENT_EFFECTS, UNMODELED and SKILL_LINES. Add a class here once its module exists.
CLASSES: dict[str, str] = {
    "mage": "wowforever.classes.mage",
    "rogue": "wowforever.classes.rogue",
    "hunter": "wowforever.classes.hunter",
    "warrior": "wowforever.classes.warrior",
    "druid": "wowforever.classes.druid",
    "paladin": "wowforever.classes.paladin",
    "priest": "wowforever.classes.priest",
    "shaman": "wowforever.classes.shaman",
    "warlock": "wowforever.classes.warlock",
}


def class_module(name: str):
    """The per-class module registered under `name`; KeyError for an unknown class."""
    import importlib

    return importlib.import_module(CLASSES[name])


class ClassEngine(Protocol):
    """A scored class's rotation behind one interface (docs/planning/2026-10-14-class-engine.md).
    The class module implements it with module-level functions; reach it through `engine(name)`."""

    def playstyle(self, cls: ClassData, ranks: Mapping[int, int]) -> str:
        """How the build fights: "melee", "ranged" or "caster"."""

    def output(self, stats: Any, spells: Sequence[SpellRank], cls: ClassData, ranks: Mapping[int, int],
               target: Target, *, pack: int = 1, drink_mana_per_second: float | None = None,
               melee: bool | None = None, sustained: bool = False) -> Output:
        """The rotation's DPS, mana use and out-of-mana DPS against `target`, over `pack` mobs.
        `sustained` asks for a raid fight's rotation, with long-cooldown buffs averaged in (#317)."""

    def aoe(self, stats: Any, spells: Sequence[SpellRank], cls: ClassData, ranks: Mapping[int, int], *,
            pack: int, mob_hp: float, armor: float) -> tuple[float, str]:
        """Seconds to clear `pack` same-level mobs of `mob_hp`, and the AoE abilities used."""

    def facts(self, stats: Any, cls: ClassData, ranks: Mapping[int, int]) -> dict[str, Any]:
        """What the rotation does, for the build description."""

    def sides(self, stats: Any, spells: Sequence[SpellRank], cls: ClassData,
              ranks: Mapping[int, int]) -> list[tuple[str | None, Any]]:
        """The build's duel sides (pvp.duel.Side), each named by the filler it casts where it has a
        choice (mage) or None; each duel scenario takes the best (#318)."""


ENGINE_MEMBERS = ("playstyle", "output", "aoe", "facts", "sides")


def engine(name: str) -> ClassEngine:
    """The class module registered under `name` as a ClassEngine; ValueError if it has none."""
    module = class_module(name)
    if not all(callable(getattr(module, member, None)) for member in ENGINE_MEMBERS):
        raise ValueError(f"no class engine for {name!r}")
    return module
