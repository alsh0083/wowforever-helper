"""Group buffs for the dungeon score (#218; plan: docs/planning/2026-10-07-party-buffs.md).

Phase 1: the catalog (config/group_buffs.toml) resolved against the game client's spell tables into
values by level (data/buffs/group_buffs.json, `wowforever group-buffs`), and the reduction of a party to
its effective buff set: one value per stacking group (two providers of a buff count once), one option per
provider for blessings, totems, curses, auras and judgements.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "config" / "group_buffs.toml"
RESOLVED = ROOT / "data" / "buffs" / "group_buffs.json"
LEVELS = tuple(range(10, 61))

# client EffectAura -> what it changes
AURA_KIND = {99: "attack_power", 124: "ranged_attack_power", 29: "stat", 137: "all_stats_pct", 290: "crit_pct",
             79: "damage_done_pct", 22: "armor", 87: "damage_taken_pct", 14: "damage_taken_flat",
             127: "ranged_attack_power_vs_target"}
STATS = {-1: "all_stats", 0: "strength", 1: "agility", 2: "stamina", 3: "intellect", 4: "spirit"}


def load_catalog(path: Path = CATALOG) -> list[dict[str, Any]]:
    return tomllib.loads(path.read_text(encoding="utf-8"))["buff"]


@dataclass
class ClientSpells:
    """The bits of the client's spell tables the catalog reads."""
    names: dict[str, str]                          # spell id -> name
    level: dict[str, int]                          # spell id -> learn level (BaseLevel)
    effects: dict[str, list[Mapping[str, str]]]    # spell id -> SpellEffect rows
    player: set[str]                               # spells on a class skill line (learnable)
    by_name: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_tables(cls, tables: Mapping[str, list[Mapping[str, str]]]) -> ClientSpells:
        effects: dict[str, list[Mapping[str, str]]] = {}
        for r in tables["SpellEffect"]:
            effects.setdefault(r["SpellID"], []).append(r)
        out = cls(names={r["ID"]: r["Name_lang"] for r in tables["SpellName"]},
                  level={r["SpellID"]: int(r["BaseLevel"] or 0) for r in tables["SpellLevels"]},
                  effects=effects, player={r["Spell"] for r in tables["SkillLineAbility"]})
        for i, n in out.names.items():
            out.by_name.setdefault(n, []).append(i)
        return out


def _effect(spell: Sequence[Mapping[str, str]], entry: Mapping[str, Any]) -> Mapping[str, str] | None:
    for e in spell:
        if "aura" in entry and int(e["EffectAura"]) != entry["aura"]:
            continue
        if "effect" in entry and int(e["Effect"]) != entry["effect"]:
            continue
        if "misc" in entry and int(e["EffectMiscValue_0"]) != entry["misc"]:
            continue
        return e
    return None


def resolve(entry: Mapping[str, Any], client: ClientSpells, talent_levels: Mapping[tuple[str, str], int]) -> dict[str, Any]:
    """{level: value} for every level a provider of that level has the buff, with the spell ids used and
    notes (ranks whose value falls below a lower rank's, which may be a Forever change or a data quirk)."""
    name = entry["spell"]
    candidates = [str(entry["spell_id"])] if "spell_id" in entry else client.by_name.get(name, [])
    ranks = []
    for sid in candidates:
        e = _effect(client.effects.get(sid, []), entry)
        if e is None:
            continue
        if "cast" not in entry and "spell_id" not in entry and sid not in client.player:
            continue
        value = abs(float(e["EffectBasePointsF"] or 0))
        ranks.append((client.level.get(sid, 0), int(sid), value, int(e["EffectMiscValue_0"])))
    ranks.sort()
    # when the buff comes from a spell the provider casts (a totem) or a talent, that gates the level
    first = 1
    if "cast" in entry:
        cast_levels = [client.level.get(s, 0) for s in client.by_name.get(entry["cast"], []) if s in client.player]
        first = min((lv for lv in cast_levels if lv > 0), default=1)
    talent = entry.get("provider", {}).get("talent")
    if talent:
        first = max(first, talent_levels.get((entry["provider"]["class"], talent), 1))
    by_level: dict[int, dict[str, Any]] = {}
    for lv in LEVELS:
        if lv < first:
            continue
        have = [r for r in ranks if r[0] <= lv] or ([ranks[0]] if ranks and ranks[0][0] == 0 else [])
        if not have:
            continue
        rank = have[-1]
        by_level[lv] = {"value": rank[2] * entry.get("stacks", 1), "spell_id": rank[1], "misc": rank[3]}
    notes = [f"rank learned at {b[0]} ({b[2]:g}) is lower than the rank at {a[0]} ({a[2]:g})"
             for a, b in zip(ranks, ranks[1:]) if b[2] < a[2] and b[0] > a[0]]
    kind = AURA_KIND.get(entry.get("aura", -1), "proc")
    if kind == "stat":
        kind = STATS.get(entry.get("misc", -1), "stat")
    return {"id": entry["id"], "kind": kind, "by_level": by_level, "notes": notes}


def build(tables: Mapping[str, list[Mapping[str, str]]], talent_levels: Mapping[tuple[str, str], int],
          catalog: Iterable[Mapping[str, Any]] | None = None, *, game_build: str = "") -> dict[str, Any]:
    client = ClientSpells.from_tables(tables)
    entries = list(catalog if catalog is not None else load_catalog())
    out = []
    for entry in entries:
        r = resolve(entry, client, talent_levels)
        out.append({**{k: v for k, v in entry.items()}, **r,
                    "by_level": {str(k): v for k, v in r["by_level"].items()}})
    return {"game_build": game_build, "source": "client spell tables (SpellName, SpellLevels, SpellEffect)",
            "buffs": out}


@dataclass(frozen=True)
class Member:
    """A party member: class, the tree they're deep in, and their role."""
    cls: str
    tree: str = ""
    role: str = "dps"


def provides(buff: Mapping[str, Any], member: Member) -> bool:
    p = buff.get("provider", {})
    if p.get("class") != member.cls:
        return False
    if p.get("role") and p["role"] != member.role:
        return False
    # a talent buff comes from a member deep in that talent's tree
    return not p.get("tree") or p["tree"] == member.tree


def options(buffs: Sequence[Mapping[str, Any]], party: Sequence[Member], level: int) -> list[list[list[dict]]]:
    """For each party member, the choices they make: a list of option lists (one list per choice set; a
    buff without a choice set is a one-option list). Only buffs the member has at `level` count."""
    out = []
    for m in party:
        mine: dict[str, list[dict]] = {}
        for b in buffs:
            cell = b["by_level"].get(str(level))
            if cell is None or not provides(b, m):
                continue
            key = b.get("choice") or f"always:{b['id']}"
            mine.setdefault(key, []).append({"id": b["id"], "stack": b["stack"], "kind": b["kind"],
                                             "reach": b["reach"], "value": cell["value"],
                                             "proc_chance": b.get("proc_chance"), "misc": cell.get("misc")})
        out.append(list(mine.values()))
    return out


def effective(picks: Iterable[Mapping[str, Any]]) -> dict[str, dict]:
    """One buff per stacking group: the strongest of those picked."""
    best: dict[str, dict] = {}
    for p in picks:
        if p["stack"] not in best or p["value"] > best[p["stack"]]["value"]:
            best[p["stack"]] = dict(p)
    return best


def talent_levels(dataset, classes: Iterable[str]) -> dict[tuple[str, str], int]:
    """(class, talent) -> the first level a provider can have it: row r needs 5r points in its tree,
    and the first point comes at 10."""
    out = {}
    for c in classes:
        for t in dataset.class_data(c).talents:
            out[(c, t.name)] = 10 + 5 * t.row
    return out


def load_resolved(path: Path = RESOLVED) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
