"""Trim cached wago.tools tables to one class's test fixture (#103/#107).

Keeps one trait tree (talents) and the class's skill lines (spells), plus the spells those
reference: talent spells, spells triggered by their effects, and the cast-time, duration and
range rows they point at. The full tables live in data/cache/wago/<build>/.

    .venv/Scripts/python tools/make_fixtures.py --build 1.60.1.70205 --tree 1111 \
        --skill-lines 253,38,39,40 --out tests/fixtures/wago-1.60.1.70205-rogue
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

TRAIT_TABLES = ("TraitTree", "TraitNode", "TraitNodeXTraitNodeEntry", "TraitNodeEntry",
                "TraitDefinition", "TraitEdge", "SkillLineXTraitTree")
SPELL_TABLES = ("SpellName", "SpellEffect", "SpellMisc", "SpellLevels", "SpellPower",
                "SpellCooldowns", "SpellTargetRestrictions", "SpellCastTimes", "SpellDuration",
                "SpellRange", "SkillLineAbility")


def read(cache: Path, table: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(cache / f"{table}.csv", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or ()), list(reader)


def write(out: Path, table: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    with open(out / f"{table}.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def trim(cache: Path, out: Path, tree: int, skill_lines: set[int]) -> dict[str, int]:
    t = {name: read(cache, name) for name in TRAIT_TABLES + SPELL_TABLES}
    rows = {name: r for name, (_, r) in t.items()}

    nodes = [r for r in rows["TraitNode"] if int(r["TraitTreeID"]) == tree]
    node_ids = {r["ID"] for r in nodes}
    links = [r for r in rows["TraitNodeXTraitNodeEntry"] if r["TraitNodeID"] in node_ids]
    entry_ids = {r["TraitNodeEntryID"] for r in links}
    entries = [r for r in rows["TraitNodeEntry"] if r["ID"] in entry_ids]
    def_ids = {r["TraitDefinitionID"] for r in entries}
    defs = [r for r in rows["TraitDefinition"] if r["ID"] in def_ids]
    kept = {
        "TraitTree": [r for r in rows["TraitTree"] if int(r["ID"]) == tree],
        "TraitNode": nodes,
        "TraitNodeXTraitNodeEntry": links,
        "TraitNodeEntry": entries,
        "TraitDefinition": defs,
        "TraitEdge": [r for r in rows["TraitEdge"]
                      if r["LeftTraitNodeID"] in node_ids or r["RightTraitNodeID"] in node_ids],
        "SkillLineXTraitTree": [r for r in rows["SkillLineXTraitTree"] if int(r["TraitTreeID"]) == tree],
        "SkillLineAbility": [r for r in rows["SkillLineAbility"] if int(r["SkillLine"]) in skill_lines],
    }

    spells = {r["Spell"] for r in kept["SkillLineAbility"]}
    for r in defs:
        spells |= {r[k] for k in ("SpellID", "OverridesSpellID", "VisibleSpellID") if r.get(k, "0") != "0"}
    for _ in range(2):  # triggered spells, two levels deep (e.g. a periodic aura's tick spell)
        spells |= {r["EffectTriggerSpell"] for r in rows["SpellEffect"]
                   if r["SpellID"] in spells and r["EffectTriggerSpell"] not in ("", "0")}

    by_spell = ("SpellEffect", "SpellMisc", "SpellLevels", "SpellPower", "SpellCooldowns",
                "SpellTargetRestrictions")
    for name in by_spell:
        kept[name] = [r for r in rows[name] if r["SpellID"] in spells]
    kept["SpellName"] = [r for r in rows["SpellName"] if r["ID"] in spells]
    misc = kept["SpellMisc"]
    for name, column in (("SpellCastTimes", "CastingTimeIndex"), ("SpellDuration", "DurationIndex"),
                         ("SpellRange", "RangeIndex")):
        wanted = {r[column] for r in misc}
        kept[name] = [r for r in rows[name] if r["ID"] in wanted]

    out.mkdir(parents=True, exist_ok=True)
    for name, (fields, _) in t.items():
        write(out, name, fields, kept[name])
    return {name: len(r) for name, r in kept.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", required=True)
    ap.add_argument("--tree", type=int, required=True, help="trait tree id")
    ap.add_argument("--skill-lines", required=True, help="comma-separated skill line ids")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default="data/cache/wago")
    args = ap.parse_args()
    counts = trim(Path(args.cache) / args.build, Path(args.out), args.tree,
                  {int(x) for x in args.skill_lines.split(",")})
    for name, n in counts.items():
        print(f"{name}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
