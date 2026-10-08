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


# --- phase 2 (#219): applying an effective buff set to a build's dungeon fight ---------------------------

MELEE_CLASSES = ("rogue", "warrior", "paladin", "druid", "shaman")   # their melee builds get totem procs
WINDFURY_HIT_SHARE = 0.9    # share of main-hand swings that land, for the procs (hit and dodge on a boss)


def _is_physical(stats) -> bool:
    return not hasattr(stats, "spell_power")


def buffed_stats(class_name: str, stats, eff: Mapping[str, Mapping[str, Any]], *, melee_build: bool = False):
    """`stats` with the effective buff set's stat-type buffs, through the class's own conversions
    (strength and agility to attack power and crit, intellect to spell crit)."""
    from dataclasses import replace

    from wowforever.melee_scenarios import HybridStats
    from wowforever.stat_weights import apply

    if isinstance(stats, HybridStats):
        inner = stats.melee if melee_build else stats.caster
        new = buffed_stats(f"{class_name}_melee" if melee_build else class_name, inner, eff)
        return replace(stats, melee=new) if melee_build else replace(stats, caster=new)
    physical = _is_physical(stats)
    name = class_name.removesuffix("_melee")
    out = stats

    def add(stat: str, amount: float):
        nonlocal out
        changed = apply(name, out, stat, amount, melee_build=False) if not class_name.endswith("_melee") else None
        if class_name.endswith("_melee"):
            from wowforever.stat_weights import _melee_apply

            changed = _melee_apply(class_name, out, stat, amount)
        if changed is not None:
            out = changed

    for b in eff.values():
        reach, kind, v = b["reach"], b["kind"], b["value"]
        if reach == "physical" and not physical or reach == "casters" and physical or reach == "melee" or reach == "target":
            continue
        if kind == "attack_power" and physical:
            out = replace(out, attack_power=out.attack_power + v)          # shouts and Might: melee AP
        elif kind == "ranged_attack_power" and physical:
            out = replace(out, ranged_attack_power=out.ranged_attack_power + v)
        elif kind in ("strength", "agility", "intellect", "stamina", "spirit"):
            add(kind, v)
        elif kind == "all_stats":
            for s in ("strength", "agility", "stamina", "intellect", "spirit"):
                add(s, v)
        elif kind == "all_stats_pct":
            for s in ("strength", "agility", "stamina", "intellect", "spirit"):
                base = getattr(out, s, 0.0) or 0.0
                add(s, base * v / 100)
        elif kind == "crit_pct":
            add("crit_pct", v)
    for b in eff.values():                  # target marks that raise the attacker's ranged attack power
        if b["kind"] == "ranged_attack_power_vs_target" and physical:
            out = replace(out, ranged_attack_power=out.ranged_attack_power + b["value"])
    return out


def armor_reduction(eff: Mapping[str, Mapping[str, Any]]) -> float:
    return sum(b["value"] for b in eff.values() if b["kind"] == "armor")


def magic_multiplier(eff: Mapping[str, Mapping[str, Any]]) -> float:
    return 1 + sum(b["value"] for b in eff.values() if b["kind"] == "damage_taken_pct") / 100


def totem_proc_dps(stats, eff: Mapping[str, Mapping[str, Any]], armor: float) -> float:
    """Windfury Totem (an extra main-hand attack with bonus attack power, 20% per hit) and Flametongue Totem
    (fire damage per main-hand hit, scaled by weapon speed as Flametongue Weapon is) for a melee build."""
    from wowforever.physical import armor_factor

    if stats.main_hand is None:
        return 0.0
    lo, hi, speed = stats.main_hand
    swings = WINDFURY_HIT_SHARE / speed
    out = 0.0
    wf = eff.get("windfury_totem")
    if wf:
        per_attack = ((lo + hi) / 2 + (stats.attack_power + wf["value"]) / 14 * speed)
        per_attack *= armor_factor(stats.level, armor) * (1 + stats.crit_pct / 100)
        out += (wf.get("proc_chance") or 0.2) * swings * per_attack
    ft = eff.get("flametongue_totem")
    if ft:
        out += swings * ft["value"] * speed / 100 * magic_multiplier(eff)
    return out


def dungeon_dps(class_name: str, stats, cls, ranks: Mapping[int, int], eff: Mapping[str, Mapping[str, Any]]) -> float:
    """A build's dungeon DPS with a party's effective buff set: buffed stats, the boss's armor after the
    party's armor debuffs (from its unsundered armor), Curse of the Elements on spell damage, totem procs."""
    from wowforever import melee_scenarios as ms
    from wowforever.classes import class_module
    from wowforever.physical import Target

    module = class_module(class_name)
    if class_name == "mage":
        from wowforever.assumptions import Assumptions
        from wowforever.scenarios import Character, default_params, raid

        buffed = buffed_stats("mage", stats, eff)
        r = raid(Character(stats.level, buffed, cls.spells, cls, dict(ranks)), default_params("dungeon", stats.level),
                 Assumptions.load())
        return r.score * magic_multiplier(eff)
    d = ms._config()["dungeon"]
    unsundered = ms._anchor_at(ms._config()["questing"]["anchors"], _level(stats))[0]
    armor = max(0.0, unsundered - armor_reduction(eff))
    melee_build = isinstance(stats, ms.HybridStats) and ms.main_tree(cls, ranks) in getattr(module, "MELEE_TREES", ())
    buffed = buffed_stats(class_name, stats, eff, melee_build=melee_build)
    out = ms.rotation_output(class_name, buffed, cls.spells, cls, ranks, Target(d["target_level_offset"], armor)).dps
    caster = getattr(module, "ENGINE", None) == "spell" and not melee_build
    if caster:
        return out * magic_multiplier(eff)
    physical = buffed.melee if isinstance(buffed, ms.HybridStats) else buffed
    if class_name in MELEE_CLASSES and _is_physical(physical) and not (class_name == "shaman" and melee_build):
        out += totem_proc_dps(physical, eff, armor)        # an Enhancement shaman's own Windfury Weapon wins
    return out


def _level(stats) -> int:
    return stats.level


# --- phase 3 (#220): compositions, weights and the grouped dungeon score ---------------------------------

WEIGHTS = ROOT / "data" / "buffs" / "group_weights.json"
TANK_SPECS = {("warrior", "Protection"): "Protection", ("paladin", "Protection"): "Protection",
              ("druid", "Guardian"): "Feral Combat"}
HEALER_SPECS = {("druid", "Restoration"), ("paladin", "Holy"), ("priest", "Discipline"), ("priest", "Holy"),
                ("shaman", "Restoration")}
# which option a provider uses for you (plan D1), by what kind of damage your build does
PREFERENCES = {
    "melee": {"blessing": ["blessing_of_might", "blessing_of_kings"], "totem_air": ["windfury_totem", "grace_of_air"],
              "curse": ["curse_of_recklessness", "curse_of_the_elements"]},
    "ranged": {"blessing": ["blessing_of_might", "blessing_of_kings"], "totem_air": ["grace_of_air", "windfury_totem"],
               "curse": ["curse_of_recklessness", "curse_of_the_elements"]},
    "caster": {"blessing": ["blessing_of_kings", "blessing_of_might"], "totem_air": ["grace_of_air", "windfury_totem"],
               "curse": ["curse_of_the_elements", "curse_of_recklessness"]},
}


def build_weights(dps_dir: Path, tank_dir: Path, healer_dir: Path) -> dict[str, Any]:
    """Parse counts per class and tree in each role, from cached Forever Logs statistics: DPS from the
    damage statistics (role=dps), tanks from role=tank, healers from the healing statistics (healer
    trees only)."""
    def counts(directory: Path, keep) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in sorted(directory.glob("*.json")):
            for cls, data in (json.loads(f.read_text(encoding="utf-8")).get("statistics") or {}).items():
                for spec, s in data["specs"].items():
                    key = keep(cls.lower(), spec)
                    if key:
                        out[key] = out.get(key, 0) + int(s["total_parses"])
        return dict(sorted(out.items()))

    def tank(c: str, s: str) -> str | None:
        return f"{c}/{TANK_SPECS[(c, s)]}" if (c, s) in TANK_SPECS else None

    def healer(c: str, s: str) -> str | None:
        return f"{c}/{s}" if (c, s) in HEALER_SPECS else None

    def dps(c: str, s: str) -> str | None:
        return f"{c}/{s}" if (c, s) not in TANK_SPECS and (c, s) not in HEALER_SPECS else None

    return {"source": "Forever Logs public statistics (phase 1), parse counts per role",
            "tank": counts(tank_dir, tank), "healer": counts(healer_dir, healer), "dps": counts(dps_dir, dps)}


def load_weights(path: Path = WEIGHTS) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compositions(weights: Mapping[str, Mapping[str, int]]) -> list[tuple[float, tuple[Member, ...]]]:
    """Every tank x healer x pair of other DPS, with its probability (DPS drawn with replacement)."""
    def shares(role: str) -> list[tuple[Member, float]]:
        total = sum(weights[role].values()) or 1
        return [(Member(k.split("/")[0], k.split("/")[1], role), n / total) for k, n in weights[role].items() if n]

    tanks, healers, dps = shares("tank"), shares("healer"), shares("dps")
    out = []
    for t, pt in tanks:
        for h, ph in healers:
            for i, (a, pa) in enumerate(dps):
                for b, pb in dps[i:]:
                    out.append((pt * ph * pa * pb * (1 if a == b else 2), (t, h, a, b)))
    return out


def player_kind(class_name: str, melee_build: bool, stats) -> str:
    if class_name == "hunter":
        return "ranged"
    return "melee" if melee_build or _is_physical(stats) else "caster"


def _pick(member_options: Sequence[Sequence[dict]], kind: str) -> list[dict]:
    prefs = PREFERENCES[kind]
    picks = []
    for opts in member_options:
        order = next((prefs[k] for k in prefs if any(o["id"] in prefs[k] for o in opts)), [])
        picks.append(min(opts, key=lambda o: order.index(o["id"]) if o["id"] in order else len(order)))
    return picks


_DIST_CACHE: dict[tuple, list] = {}


def distribution(player: Member, kind: str, level: int, *, drop: frozenset[str] = frozenset(),
                 buffs: Sequence[Mapping[str, Any]] | None = None,
                 weights: Mapping[str, Any] | None = None) -> list[tuple[float, dict[str, dict]]]:
    """Distinct effective buff sets for `player` at `level` with their probabilities. The player provides
    their own buffs too; `drop` removes stacking groups the engine already models (a hunter's own
    Trueshot Aura)."""
    key = (player, kind, level, drop)
    cacheable = buffs is None and weights is None
    if cacheable and key in _DIST_CACHE:
        return _DIST_CACHE[key]
    buffs = buffs if buffs is not None else load_resolved()["buffs"]
    weights = weights if weights is not None else load_weights()
    sets: dict[tuple, list] = {}
    for p, party in compositions(weights):
        picks = [x for m in options(buffs, (*party, player), level) for x in _pick(m, kind)]
        eff = {k: v for k, v in effective(picks).items() if k not in drop}
        sig = tuple(sorted((k, v["value"]) for k, v in eff.items()))
        if sig in sets:
            sets[sig][0] += p
        else:
            sets[sig] = [p, eff]
    out = [(p, eff) for p, eff in sets.values()]
    if cacheable:
        _DIST_CACHE[key] = out
    return out


def typical(dist: Sequence[tuple[float, Mapping[str, dict]]]) -> dict[str, dict]:
    """The buffs at least half of the weighted groups have (each at its most likely value): one set to
    score with where a full expectation is too slow (the build search, stat weights)."""
    present: dict[str, dict[float, float]] = {}
    sample: dict[tuple[str, float], dict] = {}
    for p, eff in dist:
        for k, v in eff.items():
            present.setdefault(k, {}).setdefault(v["value"], 0.0)
            present[k][v["value"]] += p
            sample[(k, v["value"])] = v
    out = {}
    for k, by_value in present.items():
        if sum(by_value.values()) >= 0.5:
            value = max(by_value, key=by_value.get)
            out[k] = sample[(k, value)]
    return out


def member_for(class_name: str, cls, ranks: Mapping[int, int]) -> Member:
    from wowforever.melee_scenarios import main_tree

    return Member(class_name, main_tree(cls, ranks), "dps")


def _drop_for(class_name: str, cls, ranks: Mapping[int, int]) -> frozenset[str]:
    tsa = next((t for t in cls.talents if t.name == "Trueshot Aura"), None)
    if class_name == "hunter" and tsa is not None and ranks.get(tsa.talent_id, 0):
        return frozenset({"trueshot_aura"})
    return frozenset()


def _kind_for(class_name: str, stats, cls, ranks) -> str:
    from wowforever import melee_scenarios as ms
    from wowforever.classes import class_module

    melee_trees = getattr(class_module(class_name), "MELEE_TREES", ())
    melee_build = isinstance(stats, ms.HybridStats) and ms.main_tree(cls, ranks) in melee_trees
    inner = stats.melee if melee_build else (stats.caster if isinstance(stats, ms.HybridStats) else stats)
    return player_kind(class_name, melee_build, inner)


def _dist_for(class_name: str, stats, cls, ranks):
    return distribution(member_for(class_name, cls, ranks), _kind_for(class_name, stats, cls, ranks),
                        _level(stats), drop=_drop_for(class_name, cls, ranks))


def typical_dungeon_dps(class_name: str, stats, cls, ranks: Mapping[int, int]) -> float:
    """Dungeon DPS with every buff at its probability-weighted value (for scores that run thousands of
    times); close to the full expectation, in one engine run."""
    return dungeon_dps(class_name, stats, cls, ranks, average(_dist_for(class_name, stats, cls, ranks)))


def grouped_dungeon(class_name: str, stats, cls, ranks: Mapping[int, int]) -> dict[str, Any]:
    """Expected dungeon DPS over every weighted group, its 10th-90th percentile range, the unbuffed value,
    and the buffs that add most on average (gain x how often the group has it)."""
    dist = _dist_for(class_name, stats, cls, ranks)
    results = sorted((dungeon_dps(class_name, stats, cls, ranks, eff), p) for p, eff in dist)
    total = sum(p for _, p in results) or 1.0
    expected = sum(v * p for v, p in results) / total

    def pct(q: float) -> float:
        acc = 0.0
        for v, p in results:
            acc += p / total
            if acc >= q:
                return v
        return results[-1][0]

    base = dungeon_dps(class_name, stats, cls, ranks, {})
    gains = {k: dungeon_dps(class_name, stats, cls, ranks, {k: v}) - base for k, v in average(dist).items()}   # expected contribution
    top = [k for k, g in sorted(gains.items(), key=lambda kv: -kv[1]) if g > 0.01 * base][:3]
    return {"score": round(expected, 1), "low": round(pct(0.1), 1), "high": round(pct(0.9), 1),
            "unbuffed": round(base, 1), "top_buffs": top}


def average(dist: Sequence[tuple[float, Mapping[str, dict]]]) -> dict[str, dict]:
    """Every buff at its probability-weighted value (a Sunder in half the groups counts half; Windfury's
    proc chance scales the same way): one set to score with where the full expectation is too slow
    (the build search, stat weights). Smooth, unlike a majority cut."""
    total = sum(p for p, _ in dist) or 1.0
    out: dict[str, dict] = {}
    for p, eff in dist:
        for k, v in eff.items():
            cell = out.setdefault(k, {**v, "value": 0.0, "proc_chance": 0.0 if v.get("proc_chance") else None, "_p": 0.0})
            cell["_p"] += p / total
            cell["value"] += v["value"] * p / total
    for k, cell in out.items():
        if cell.get("proc_chance") is not None:          # a proc keeps its own size; how often it's there scales
            cell["proc_chance"] = (out[k].get("proc_chance") or 0) + 0.2 * cell["_p"]
            cell["value"] = cell["value"] / cell["_p"]
        cell.pop("_p")
    return out
