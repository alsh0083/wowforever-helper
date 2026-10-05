"""Assemble everything the dashboard shows: per build, a legal point order, scenario scores at
level checkpoints, and spell-training milestones, as one JSON-ready payload.

Point orders: a build's own `order` when it has one, otherwise the optimizer's, valuing each
partial build by questing kills/hour at that level (the order matters while leveling).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, replace
from typing import Any

from wowforever.assumptions import Assumptions
from wowforever.builds import Build
from wowforever.calc.pvp_axes import control, survival
from wowforever.optimizer import optimize_order
from wowforever.rules import check_order, points_available
from wowforever.scenarios import Character, aoe_curve, best_rank, default_params, questing, raid
from wowforever.schema import ClassData, SpellRank
from wowforever.stats import StatTable

CHECKPOINTS = (20, 30, 40, 50, 60)


def ranks_at(order: Sequence[int], level: int, cls: ClassData) -> dict[int, int]:
    """Talent ranks after spending the points available at `level`."""
    return dict(Counter(order[: points_available(level, cls.rules)]))


def leveling_value(cls: ClassData, spells: tuple[SpellRank, ...], stats: StatTable,
                   assumptions: Assumptions, primary_spell: str = ""):
    """Optimizer value function: questing kills/hour of a partial build at a level.

    With a primary spell, questing uses it whenever it's learned, so talents that improve it
    count from the start instead of only once it beats the other fillers. Ties (talents that
    don't change kills/hour now) break toward the talent worth more at max level."""
    top = cls.rules.max_level
    params = {lvl: default_params("questing", lvl) for lvl in range(cls.rules.first_talent_level, top + 1)}
    if primary_spell:
        params = {lvl: replace(p, fillers=(primary_spell,)) if best_rank(spells, primary_spell, lvl)
                  else p for lvl, p in params.items()}

    def kills(ranks: dict[int, int], level: int) -> float:
        return questing(Character(level, stats.at(level), spells, cls, ranks), params[level], assumptions).score

    def value(ranks: dict[int, int], level: int) -> float:
        return kills(ranks, level) + 1e-3 * kills(ranks, top)

    return value


def build_order(build: Build, cls: ClassData, spells, stats, assumptions) -> tuple[list[int], str]:
    """(talent id per point, how the order was made)."""
    if build.order:
        return build.order_ids(cls), "hand-written"
    must = {cls.talent_named(n).talent_id: lvl for n, lvl in build.must_have_by.items()}
    order = optimize_order(cls, build.final_ids(cls), must,
                           leveling_value(cls, spells, stats, assumptions, build.primary_spell))
    return order, "optimized for questing kills/hour"


def score_build(order: Sequence[int], cls: ClassData, spells, stats: StatTable,
                assumptions: Assumptions) -> dict[str, dict[int, dict[str, Any]]]:
    """Scenario results at each checkpoint level (raid at max level only)."""
    scores: dict[str, dict[int, dict[str, Any]]] = {"questing": {}, "aoe": {}, "raid": {},
                                                    "survival": {}, "control": {}}
    for level in CHECKPOINTS:
        char = Character(level, stats.at(level), spells, cls, ranks_at(order, level, cls))
        q = questing(char, default_params("questing", level), assumptions)
        a = aoe_curve(char, default_params("aoe", level), assumptions)
        scores["questing"][level] = {"score": round(q.score, 1), "unit": q.unit, "spell": q.details["spell"]}
        scores["aoe"][level] = {"score": a.score, "unit": a.unit, "spell": a.details["aoe_spell"],
                                "break_even": a.details["break_even"]}
        filler = best_rank(spells, q.details["spell"], level)
        for name, axis in (("survival", survival), ("control", control)):
            result = axis(char, filler)
            scores[name][level] = {"score": round(result.score, 3), "unit": "0-1",
                                   "components": {k: round(v, 3) for k, v in result.components.items()}}
        if level == cls.rules.max_level:
            r = raid(char, default_params("raid", level), assumptions)
            scores["raid"][level] = {"score": round(r.score, 1), "unit": r.unit, "spell": r.details["spell"],
                                     "time_to_oom": r.details["time_to_oom"]}
    return scores


def sensitivity(order: Sequence[int], cls: ClassData, spells, stats: StatTable,
                assumptions: Assumptions) -> list[str]:
    """Which assumption switches change this build's level-60 AoE break-even or raid DPS."""
    notes = []
    char_args = (cls.rules.max_level, stats.at(cls.rules.max_level), spells, cls,
                 ranks_at(order, cls.rules.max_level, cls))
    base_aoe = aoe_curve(Character(*char_args), default_params("aoe", 60), assumptions).score
    base_raid = raid(Character(*char_args), default_params("raid", 60), assumptions).score
    for name, entry in assumptions.entries.items():
        for option in entry.options:
            if option == assumptions[name]:
                continue
            alt = assumptions.with_values(**{name: option})
            aoe = aoe_curve(Character(*char_args), default_params("aoe", 60), alt).score
            dps = raid(Character(*char_args), default_params("raid", 60), alt).score
            if aoe != base_aoe:
                notes.append(f"{name}={option}: AoE break-even {base_aoe:g} -> {aoe:g}")
            if abs(dps - base_raid) > 0.05:
                notes.append(f"{name}={option}: raid DPS {base_raid:.1f} -> {dps:.1f}")
    return notes


def spell_milestones(spells: Sequence[SpellRank], max_level: int,
                     talent_spell_ids: frozenset[int] = frozenset()) -> list[dict[str, Any]]:
    """Trainer-taught ranks of damage and key utility spells, by level. A talent grants its own
    spell (rank 1 of Ice Lance, Pyroblast, ...; all of Ice Block, Cold Snap, ...), so those exact
    spell ids are skipped; higher ranks of talent spells are trained and stay."""
    return [
        {"level": s.level, "spell": s.name, "rank": s.rank}
        for s in sorted(spells, key=lambda s: (s.level, s.name, s.rank))
        if s.level <= max_level and s.spell_id not in talent_spell_ids
        and (s.min_damage or s.periodic_damage or s.name in KEY_UTILITY)
    ]


KEY_UTILITY = frozenset({"Frost Nova", "Blink", "Counterspell", "Polymorph", "Ice Block", "Ice Barrier",
                         "Mana Shield", "Evocation", "Cold Snap", "Presence of Mind", "Arcane Power"})


def build_report(cls: ClassData, spells: tuple[SpellRank, ...], builds: Sequence[Build],
                 stats: StatTable, assumptions: Assumptions, dataset: dict[str, Any]) -> dict[str, Any]:
    """JSON-ready payload for the dashboard."""
    trees = {t.tree_id: t.name for t in cls.trees}
    payload_builds = []
    for b in builds:
        order, how = build_order(b, cls, spells, stats, assumptions)
        problems = check_order(cls, order)
        if problems:
            raise ValueError(f"{b.id}: illegal order: {problems}")
        payload_builds.append({
            "id": b.id, "name": b.name, "pair": b.pair, "variant": b.variant,
            "summary": b.summary, "gives_up": list(b.gives_up),
            "must_have_by": b.must_have_by, "order": order, "order_source": how,
            "open_points": points_available(cls.rules.max_level, cls.rules) - len(order),
            "scores": score_build(order, cls, spells, stats, assumptions),
            "sensitivity": sensitivity(order, cls, spells, stats, assumptions),
        })
    return {
        "dataset": dataset,
        "rules": asdict(cls.rules),
        "trees": [{"id": t.tree_id, "name": t.name} for t in cls.trees],
        "talents": {
            str(t.talent_id): {
                "name": t.name, "tree": trees[t.tree_id], "row": t.row, "col": t.col,
                "max_rank": t.max_rank, "icon": t.icon, "rank_text": list(t.rank_text),
                "classic_status": t.classic_status,
                "prerequisite": t.prerequisite.talent_id if t.prerequisite else None,
            }
            for t in cls.talents
        },
        "builds": payload_builds,
        "spell_milestones": spell_milestones(spells, cls.rules.max_level,
                                             frozenset(t.spell_id for t in cls.talents)),
        "assumptions": {n: {"value": a.value, "why": a.why, "tested": a.tested}
                        for n, a in assumptions.entries.items()},
        "caveats": [
            "Questing and raid scenarios use a filler-plus-weaves rotation (Fire Blast, Scorch, "
            "Pyroblast, Ice Lance); Combustion, utility and PvP talents are not modeled yet (#57).",
            "Stats, mob HP and mana budgets are rough Classic-era defaults (low confidence).",
        ],
    }


def report_from_dataset(dataset_path, class_name: str = "mage") -> dict[str, Any]:
    """Load a saved dataset (from `python -m wowforever update`) and build the report payload."""
    from pathlib import Path

    from wowforever.builds import load_builds
    from wowforever.schema import Dataset

    from wowforever.classes import mage
    from wowforever.effects import attach_effects

    ds = Dataset.load(Path(dataset_path))
    # effects are the tool's reading of the rank text: re-derive them with the current rules,
    # so rule changes apply without refetching the game data
    cls, _ = attach_effects(ds.class_data(class_name), mage.TALENT_EFFECTS, mage.UNMODELED)
    meta = {"version": ds.version, "game_build": ds.game_build,
            "sources": [{"source": p.source, "game_build": p.game_build, "data_version": p.data_version,
                         "fetched_at": p.fetched_at} for p in ds.provenance]}
    return build_report(cls, cls.spells, load_builds(), StatTable.load(class_name), Assumptions.load(), meta)
