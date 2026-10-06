"""Normalized, class-agnostic talent and spell data.

Both sources (wago.tools DB2 tables, wowforevertalent.com) map into these types; everything
downstream reads only these. Class-specific knowledge (school interactions, how effects are
tagged) lives in `wowforever.classes`, never here.

Identity: talents are keyed by the game's Talent ID and spells by Spell ID, because grid positions
and names can change between patches. Rows and columns are 0-indexed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

# Effect kinds the calculator understands. Extend here (one place) when a new kind is needed.
EFFECT_KINDS = frozenset({
    "damage_pct",       # % more damage
    "crit_chance",      # + crit chance (percentage points)
    "crit_damage_pct",  # % more crit damage / bonus
    "hit_chance",       # + hit chance (percentage points)
    "cast_time",        # change to cast time, seconds (negative = faster)
    "cooldown",         # change to cooldown, seconds
    "mana_cost_pct",    # % change to mana cost
    "energy_cost",      # flat change to an ability's energy cost (negative = cheaper)
    "rage_cost",        # flat change to an ability's rage cost (negative = cheaper)
    "dodge_reduction",  # percentage points off the target's dodge and parry
    "armor_pen",        # % of the target's armor ignored
    "ap_from_int_pct",  # attack power gained as % of Intellect (Careful Aim)
    "stat_pct",         # % more of a primary stat; applies_to names the stat
    "proc_chance",      # % chance to trigger something
    "dot_pct",          # % of damage dealt again as damage over time (e.g. Ignite)
    "pushback_pct",     # % reduction of spell pushback
    "range",            # change to range, yards
    "duration",         # change to duration, seconds
    "slow_pct",         # movement slow, %
    "control",          # root/stun/freeze/interrupt effect (value = duration or chance)
    "defensive",        # absorb/immunity/damage reduction
    "resource",         # mana regen / return
    "regen_while_casting",  # share of spirit regen that continues while casting (Arcane Meditation)
    "grants_spell",     # talent teaches a spell (value unused)
    "other",            # understood by a human, not modeled yet
})
CLASSIC_STATUS = frozenset({"same", "changed", "moved", "new"})  # moved = same effect, new position


class SchemaError(ValueError):
    """Dataset violates the schema's structural rules."""


@dataclass(frozen=True)
class Provenance:
    source: str              # "wago.tools" | "wowforevertalent.com" | "in-game test" | ...
    game_build: str          # e.g. "1.60.1.70205"
    data_version: str        # source's own version id, or the game build when it has none
    fetched_at: str          # ISO 8601 UTC
    snapshot_sha256: str     # hash of the raw snapshot this record was parsed from


@dataclass(frozen=True)
class Effect:
    kind: str
    values: tuple[float, ...]          # one value per rank
    applies_to: tuple[str, ...] = ()   # spell names, school names, or "all"; empty = the talent itself
    note: str = ""                     # human-readable qualifier the numbers don't capture


@dataclass(frozen=True)
class Prerequisite:
    talent_id: int
    rank: int                          # rank of the prerequisite talent required


@dataclass(frozen=True)
class Talent:
    talent_id: int
    name: str
    tree_id: int
    row: int
    col: int
    max_rank: int
    rank_spell_ids: tuple[int, ...]
    rank_text: tuple[str, ...]
    prerequisite: Prerequisite | None = None
    effects: tuple[Effect, ...] = ()
    classic_status: str | None = None  # same/changed/moved/new vs Classic; None = unknown
    icon: str = ""
    spell_id: int = 0                  # talent's spell when all ranks share one (trait-based trees)


@dataclass(frozen=True)
class Tree:
    tree_id: int
    name: str
    talent_ids: tuple[int, ...]


@dataclass(frozen=True)
class SpellRank:
    spell_id: int
    name: str
    rank: int
    level: int                         # level the rank is learned
    schools: tuple[str, ...]           # e.g. ("fire",), ("fire", "frost") for Frostfire Bolt
    cast_time: float                   # seconds; 0 = instant
    cooldown: float = 0.0
    mana_cost: int = 0
    min_damage: float = 0.0
    max_damage: float = 0.0
    coefficient: float = 0.0           # direct spell-power coefficient
    periodic_damage: float = 0.0       # total over duration
    periodic_coefficient: float = 0.0
    duration: float = 0.0
    range: float = 0.0
    note: str = ""
    tick_period: float = 0.0           # seconds between periodic ticks; 0 = no periodic part
    damage_per_level: float = 0.0      # base damage gained per caster level above `level`...
    scaling_max_level: int = 0         # ...up to this level (0 = no scaling)
    slow_pct: float = 0.0              # movement slow applied, %
    max_targets: int = 0               # AoE target cap; 0 = no cap in client data
    channeled: bool = False            # casting occupies the full `duration`
    absorb: float = 0.0                # damage absorbed by a shield (Ice Barrier, Mana Shield, Wards)
    root: float = 0.0                  # seconds the target is rooted (Frost Nova)
    stun: float = 0.0                  # seconds the target is stunned
    immunity: float = 0.0              # seconds of immunity for the caster (Ice Block)
    incapacitate: float = 0.0          # seconds the target is incapacitated (Polymorph)
    interrupt_lockout: float = 0.0     # seconds a school is locked out on interrupt (Counterspell)
    fear: float = 0.0                  # seconds the target is feared (Fear, Psychic Scream)
    disorient: float = 0.0             # seconds the target is disoriented (Scatter Shot, Blind)
    energy_cost: int = 0               # rogue energy (SpellPower PowerType 3, #121)
    rage_cost: int = 0                 # warrior rage (SpellPower PowerType 1, stored in tenths, #162)
    weapon_bonus: float = 0.0          # flat damage added to the weapon hit (effect 121 or 58 base points)
    weapon_normalized: bool = False    # effect 121: normalized weapon damage (speed set by weapon type)
    weapon_pct: float = 0.0            # effect 31 base points, e.g. 150 for 150%; 0 = no percentage effect
    weapon_hits: int = 0               # weapon strikes per use: 1 for a direct effect, or the triggered count
    per_combo_point: float = 0.0       # extra damage per combo point (EffectPointsPerResource of the damage effect)
    combo_points: int = 0              # combo points awarded (effect 30 with EffectMiscValue_0 == 4)
    haste_pct: float = 0.0             # melee haste aura (aura 319) base points


@dataclass(frozen=True)
class Rules:
    first_talent_level: int = 10
    max_level: int = 60
    points_per_row: int = 5            # points in the tree required per row above the target row


@dataclass(frozen=True)
class ClassData:
    class_name: str                    # e.g. "mage"
    trees: tuple[Tree, ...]
    talents: tuple[Talent, ...]
    spells: tuple[SpellRank, ...] = ()
    rules: Rules = field(default_factory=Rules)

    def talent(self, talent_id: int) -> Talent:
        for t in self.talents:
            if t.talent_id == talent_id:
                return t
        raise KeyError(talent_id)

    def talent_named(self, name: str) -> Talent:
        matches = [t for t in self.talents if t.name.lower() == name.lower()]
        if len(matches) != 1:
            raise KeyError(f"{name!r}: {len(matches)} matches")
        return matches[0]


@dataclass(frozen=True)
class Dataset:
    version: str                       # dataset version id, keyed to the game build
    game_build: str
    classes: tuple[ClassData, ...]
    provenance: tuple[Provenance, ...]
    schema_version: int = SCHEMA_VERSION

    def class_data(self, class_name: str) -> ClassData:
        for c in self.classes:
            if c.class_name == class_name:
                return c
        raise KeyError(class_name)

    # ---- validation -------------------------------------------------------------------------

    def validate(self) -> None:
        """Raise SchemaError listing every structural problem found."""
        problems: list[str] = []
        if not self.provenance:
            problems.append("dataset has no provenance")
        for c in self.classes:
            problems += _validate_class(c)
        if problems:
            raise SchemaError("\n".join(problems))

    # ---- JSON -------------------------------------------------------------------------------

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=1, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> Dataset:
        return _dataset_from_dict(json.loads(text))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json() + "\n", encoding="utf-8", newline="\n")

    @classmethod
    def load(cls, path: Path) -> Dataset:
        return cls.from_json(path.read_text(encoding="utf-8"))


def _validate_class(c: ClassData) -> list[str]:
    p: list[str] = []
    where = c.class_name
    by_id = {}
    for t in c.talents:
        if t.talent_id in by_id:
            p.append(f"{where}: duplicate talent id {t.talent_id}")
        by_id[t.talent_id] = t
    tree_ids = {tr.tree_id for tr in c.trees}
    listed = [tid for tr in c.trees for tid in tr.talent_ids]
    if sorted(listed) != sorted(by_id):
        p.append(f"{where}: tree talent lists do not match talents")
    positions: dict[tuple[int, int, int], int] = {}
    for t in c.talents:
        tw = f"{where}/{t.name}"
        if t.tree_id not in tree_ids:
            p.append(f"{tw}: unknown tree {t.tree_id}")
        if t.row < 0 or t.col < 0:
            p.append(f"{tw}: negative position")
        pos = (t.tree_id, t.row, t.col)
        if pos in positions:
            p.append(f"{tw}: shares position {pos} with talent {positions[pos]}")
        positions[pos] = t.talent_id
        if t.max_rank < 1:
            p.append(f"{tw}: max_rank < 1")
        if len(t.rank_spell_ids) not in (0, t.max_rank):
            p.append(f"{tw}: {len(t.rank_spell_ids)} rank spell ids for max_rank {t.max_rank}")
        if len(t.rank_text) not in (0, t.max_rank):
            p.append(f"{tw}: {len(t.rank_text)} rank texts for max_rank {t.max_rank}")
        if t.classic_status is not None and t.classic_status not in CLASSIC_STATUS:
            p.append(f"{tw}: bad classic_status {t.classic_status!r}")
        for e in t.effects:
            if e.kind not in EFFECT_KINDS:
                p.append(f"{tw}: unknown effect kind {e.kind!r}")
            if len(e.values) != t.max_rank:
                p.append(f"{tw}: effect {e.kind} has {len(e.values)} values for max_rank {t.max_rank}")
        if t.prerequisite:
            pre = by_id.get(t.prerequisite.talent_id)
            if pre is None:
                p.append(f"{tw}: prerequisite {t.prerequisite.talent_id} missing")
            else:
                if pre.tree_id != t.tree_id or pre.row >= t.row:
                    p.append(f"{tw}: prerequisite {pre.name} must be earlier in the same tree")
                if not 1 <= t.prerequisite.rank <= pre.max_rank:
                    p.append(f"{tw}: prerequisite rank {t.prerequisite.rank} out of range")
    for s in c.spells:
        if s.rank < 1 or s.level < 1 or s.cast_time < 0 or s.min_damage > s.max_damage:
            p.append(f"{where}/{s.name} rank {s.rank}: invalid spell rank values")
    return p


def _dataset_from_dict(d: dict[str, Any]) -> Dataset:
    if d.get("schema_version") != SCHEMA_VERSION:
        raise SchemaError(f"unsupported schema_version {d.get('schema_version')}")
    return Dataset(
        version=d["version"],
        game_build=d["game_build"],
        provenance=tuple(Provenance(**p) for p in d["provenance"]),
        classes=tuple(_class_from_dict(c) for c in d["classes"]),
    )


def _class_from_dict(c: dict[str, Any]) -> ClassData:
    return ClassData(
        class_name=c["class_name"],
        trees=tuple(Tree(tr["tree_id"], tr["name"], tuple(tr["talent_ids"])) for tr in c["trees"]),
        talents=tuple(_talent_from_dict(t) for t in c["talents"]),
        spells=tuple(SpellRank(**{**s, "schools": tuple(s["schools"])}) for s in c["spells"]),
        rules=Rules(**c["rules"]),
    )


def _talent_from_dict(t: dict[str, Any]) -> Talent:
    pre = t["prerequisite"]
    return Talent(
        **{k: v for k, v in t.items() if k not in ("prerequisite", "effects", "rank_spell_ids", "rank_text")},
        rank_spell_ids=tuple(t["rank_spell_ids"]),
        rank_text=tuple(t["rank_text"]),
        prerequisite=Prerequisite(**pre) if pre else None,
        effects=tuple(
            Effect(e["kind"], tuple(e["values"]), tuple(e["applies_to"]), e["note"]) for e in t["effects"]
        ),
    )
