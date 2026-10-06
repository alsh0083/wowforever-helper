"""Assemble everything the dashboard shows: per build, a legal point order, scenario scores at
level checkpoints, and spell-training milestones, as one JSON-ready payload.

Point orders: a build's own `order` when it has one, otherwise the optimizer's, valuing each
partial build by questing kills/hour at that level (the order matters while leveling).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, replace
from typing import Any

from wowforever.assumptions import Assumptions
from wowforever.builds import Build
from wowforever.calc.pvp_axes import control, survival
from wowforever.checklist import checklist
from wowforever.classes import class_module as _class_module
from wowforever.consensus import Consensus
from wowforever.focus import pve_score_fn, pvp_score_fn
from wowforever.optimizer import optimize_order
from wowforever.shortlist import build_shortlist
from wowforever.pvp.battleground import best_battleground
from wowforever.pvp.duel import best_scenario_scores, load_kits
from wowforever.rules import check_order, points_available
from wowforever.scenarios import (Character, aoe_curve, best_rank, default_params, questing, raid,
                                  usable_fillers)
from wowforever.schema import ClassData, SpellRank
from wowforever.stats import StatTable

CHECKPOINTS = (20, 30, 40, 50, 60)
SHORTLIST_MARGIN = 0.05  # owner decision (#28): model picks must beat the standard by more than 5%


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
    kits = load_kits()
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
        fillers = usable_fillers(char, default_params("questing", level).fillers, level, assumptions)
        for name, result in best_scenario_scores(char, fillers, kits).items():
            scores.setdefault(name, {})[level] = {
                "score": round(result["score"], 3), "unit": "duel 0-1", "spell": result["spell"],
                "matchups": {k: round(v, 3) for k, v in result["matchups"].items()}}
        d = raid(char, default_params("dungeon", level), assumptions)
        scores.setdefault("dungeon", {})[level] = {"score": round(d.score, 1), "unit": "dps",
                                                   "spell": d.details["spell"]}
        bg = best_battleground(char, fillers, assumptions)
        scores.setdefault("battleground", {})[level] = {
            "score": round(bg["score"], 3), "unit": "0-1", "spell": bg["spell"],
            "components": {k: round(v, 3) for k, v in bg["components"].items()}}
        if level == cls.rules.max_level:
            r = raid(char, default_params("raid", level), assumptions)
            scores["raid"][level] = {"score": round(r.score, 1), "unit": r.unit, "spell": r.details["spell"],
                                     "time_to_oom": r.details["time_to_oom"],
                                     "raw_dps": round(r.details["dps"], 1),
                                     "fallback_spell": r.details["fallback_spell"]}
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


def shortlist_payload(cls: ClassData, builds: Sequence[Build], stats_60, assumptions: Assumptions) -> list[dict]:
    """Archetype x focus slots (#28) with model picks as talent-name changes against their seed."""
    consensus = Consensus.load()
    arch = consensus.archetypes
    fns = {"PvP": pvp_score_fn(cls, stats_60, assumptions, load_kits(), consensus),
           "PvE": pve_score_fn(cls, stats_60, assumptions)}
    slots = build_shortlist(cls, list(builds), fns, margin=SHORTLIST_MARGIN, deep=arch["deep"],
                            hybrid=arch["hybrid"], recognized=tuple(arch["recognized"]))
    names = {t.talent_id: t.name for t in cls.talents}
    by_id = {b.id: b.final_ids(cls) for b in builds}
    out = []
    for s in slots:
        d = s.as_dict()
        if s.model_pick is not None:
            seed = by_id.get(s.standard) or (by_id.get(s.qualifying[0]) if s.qualifying else {}) or {}
            d["model_pick"] = {names[t]: r for t, r in sorted(s.model_pick.items())}
            d["model_pick_changes"] = [
                {"talent": names[t], "from": seed.get(t, 0), "to": s.model_pick.get(t, 0)}
                for t in sorted(set(seed) | set(s.model_pick)) if seed.get(t, 0) != s.model_pick.get(t, 0)]
            d["model_pick_seed"] = s.standard or (s.qualifying[0] if s.qualifying else None)
        out.append(d)
    return out


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
            "id": b.id, "name": b.name, "pair": b.pair, "variant": b.variant, "origin": b.origin,
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
        "shortlist": shortlist_payload(cls, builds, stats.at(cls.rules.max_level), assumptions),
        "spell_milestones": spell_milestones(spells, cls.rules.max_level,
                                             frozenset(t.spell_id for t in cls.talents)),
        "assumptions": {n: {"value": a.value, "why": a.why, "tested": a.tested}
                        for n, a in assumptions.entries.items()},
        "checklist": [asdict(item) for item in checklist(assumptions)],
        "caveats": [
            "Questing and raid scenarios use a filler-plus-weaves rotation (Fire Blast, Scorch, "
            "Pyroblast, Ice Lance); Combustion, utility and PvP talents are not modeled yet (#57).",
            "Stats, mob HP and mana budgets are rough Classic-era defaults (low confidence).",
            "Respecs: Dual Specialization reportedly unlocks at 40, so a PvP and a PvE build can be "
            "carried together from then on. Before 40 a respec costs gold at a class trainer; the "
            "launch price is unpublished (beta charges 1 silver; guides assume Classic's 1g, 5g, then "
            "+5g per respec up to 50g). See docs/research/forever-facts.md.",
        ],
    }


ROUTE_CAVEAT = ("Routes only: this class's builds are community standards in a legal point order "
                "(top rows first). Scores, model picks and optimized orders wait on the melee and "
                "ranged damage engine (#111).")


def route_report(cls: ClassData, builds: Sequence[Build], dataset: dict[str, Any], *,
                 hybrids: Sequence[str] = (), scoring_note: str = "") -> dict[str, Any]:
    """Dashboard payload for a class the calculator can't score yet (#105): each build as a legal
    point order, placed in the archetype x focus matrix without scores."""
    from wowforever.consensus import Consensus
    from wowforever.optimizer import optimize_order
    from wowforever.shortlist import classify

    trees = {t.tree_id: t.name for t in cls.trees}
    deep = Consensus.load().archetypes["deep"]
    hybrid = Consensus.load().archetypes["hybrid"]
    payload_builds, placed = [], {}
    for b in builds:
        if b.order:
            order, how = b.order_ids(cls), "hand-written"
        else:
            must = {cls.talent_named(n).talent_id: lvl for n, lvl in b.must_have_by.items()}
            final = b.final_ids(cls)
            tree_of = {tid: t.tree_id for t in cls.trees for tid in t.talent_ids}
            weight = {tree: sum(r for tid, r in final.items() if tree_of[tid] == tree) for tree in set(tree_of.values())}
            # the build's biggest tree first, top rows first within it, while every point stays legal
            order = optimize_order(cls, final, must,
                                   lambda ranks, level: sum(weight[tree_of[t]] * r for t, r in ranks.items()))
            how = "legal order (main tree first), not optimized yet"
        problems = check_order(cls, order)
        if problems:
            raise ValueError(f"{b.id}: illegal order: {problems}")
        payload_builds.append({
            "id": b.id, "name": b.name, "pair": b.pair, "variant": b.variant, "origin": b.origin,
            "summary": b.summary, "gives_up": list(b.gives_up), "must_have_by": b.must_have_by,
            "order": order, "order_source": how,
            "open_points": points_available(cls.rules.max_level, cls.rules) - len(order),
            "scores": {}, "sensitivity": [],
        })
        label = classify(cls, b.final_ids(cls), deep=deep, hybrid=hybrid, recognized=tuple(hybrids))
        if label:
            placed.setdefault((label, b.variant), []).append(b.id)
    archetypes = [f"deep {t.name}" for t in sorted(cls.trees, key=lambda t: t.tree_id)] + list(hybrids)
    shortlist = [{
        "archetype": a, "focus": focus,
        "standard": (placed.get((a, focus)) or [None])[0], "standard_score": None,
        "model_pick": None, "model_pick_score": None, "candidates": {},
        "qualifying": placed.get((a, focus), []),
    } for a in archetypes for focus in ("PvP", "PvE")]
    return {
        "class": cls.class_name, "engine": False, "scoring_note": scoring_note,
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
        "shortlist": shortlist,
        "spell_milestones": spell_milestones(cls.spells, cls.rules.max_level,
                                             frozenset(t.spell_id for t in cls.talents)),
        "assumptions": {},
        "checklist": [],
        "caveats": [ROUTE_CAVEAT],
    }


MELEE_CAVEAT = ("Melee and ranged model (#111): expected-value rotations against Classic combat-table "
                "rules; poisons, Backstab, Hack and Slash and hunter pet details aren't modeled yet, and "
                "base stats are estimates. PvP scores use the mage's duel model from this class's side "
                "(#134); stealth openers, Evasion, Vanish, Deterrence and Feign Death aren't counted yet.")


def melee_report(class_name: str, cls: ClassData, builds: Sequence[Build], dataset: dict[str, Any], *,
                 hybrids: Sequence[str] = ()) -> dict[str, Any]:
    """Scored report for rogue and hunter (#133): leveling orders optimized for questing kills/hour,
    questing/dungeon/raid scores per checkpoint, and PvE model picks in the shortlist."""
    from wowforever import melee_scenarios as ms
    from wowforever.consensus import Consensus
    from wowforever.optimizer import optimize_order
    from wowforever.rules import points_available
    from wowforever.shortlist import build_shortlist

    payload = route_report(cls, builds, dataset, hybrids=hybrids)
    # tank and healer trees stay unscored (planning round 2, Q3): routes only
    unscored = {f"deep {t}" for t in getattr(_class_module(class_name), "UNSCORED_TREES", ())}
    unscored_builds = ({b for s in payload["shortlist"] if s["archetype"] in unscored for b in s["qualifying"]}
                       | set(getattr(_class_module(class_name), "UNSCORED_BUILDS", ())))
    table = ms.stat_table(class_name)
    top = cls.rules.max_level
    spells = cls.spells

    def kills(ranks: Mapping[int, int], level: int) -> float:
        return ms.questing(class_name, table.at(level), spells, cls, ranks)

    def value(ranks: dict[int, int], level: int) -> float:
        return kills(ranks, level) + 1e-3 * kills(ranks, top)

    by_id = {b.id: b for b in builds}
    for entry in payload["builds"]:
        build = by_id[entry["id"]]
        if not build.order:
            must = {cls.talent_named(n).talent_id: lvl for n, lvl in build.must_have_by.items()}
            entry["order"] = optimize_order(cls, build.final_ids(cls), must, value)
            entry["order_source"] = "optimized for questing kills/hour"
            entry["open_points"] = points_available(top, cls.rules) - len(entry["order"])
        order = entry["order"]
        scores: dict[str, dict[int, dict[str, Any]]] = {"questing": {}, "dungeon": {}, "raid": {}}
        for level in CHECKPOINTS:
            ranks = ranks_at(order, level, cls)
            stats = table.at(level)
            scores["questing"][level] = {"score": round(kills(ranks, level), 1), "unit": "kills/hour"}
            scores["dungeon"][level] = {"score": round(ms.dungeon(class_name, stats, spells, cls, ranks), 1),
                                        "unit": "dps"}
            if level == top:
                scores["raid"][level] = {"score": round(ms.raid(class_name, stats, spells, cls, ranks), 1),
                                         "unit": "dps"}
        entry["scores"] = {} if entry["id"] in unscored_builds else scores

    arch = Consensus.load().archetypes
    stats_top = table.at(top)
    from wowforever.pvp.class_pvp import pvp_score
    from wowforever.pvp.duel import load_kits

    kits = load_kits()
    fns = {"PvE": lambda ranks: ms.pve_score(class_name, stats_top, spells, cls, ranks),
           "PvP": lambda ranks: pvp_score(class_name, stats_top, spells, cls, ranks, kits)}
    slots = build_shortlist(cls, list(builds), fns, margin=SHORTLIST_MARGIN, deep=arch["deep"],
                            hybrid=arch["hybrid"], recognized=tuple(hybrids))
    names = {t.talent_id: t.name for t in cls.talents}
    finals = {b.id: b.final_ids(cls) for b in builds}
    shortlist = []
    for slot in slots:
        d = slot.as_dict()
        if slot.archetype in unscored or (slot.standard in unscored_builds and slot.focus == "PvE"):
            d.update(standard_score=None, model_pick=None, model_pick_score=None, candidates={})
        elif slot.model_pick is not None:
            seed_id = slot.standard or (slot.qualifying[0] if slot.qualifying else None)
            seed = finals.get(seed_id, {})
            d["model_pick"] = {names[t]: r for t, r in sorted(slot.model_pick.items())}
            d["model_pick_changes"] = [{"talent": names[t], "from": seed.get(t, 0), "to": slot.model_pick.get(t, 0)}
                                       for t in sorted(set(seed) | set(slot.model_pick))
                                       if seed.get(t, 0) != slot.model_pick.get(t, 0)]
            d["model_pick_seed"] = seed_id
        shortlist.append(d)
    payload.update(engine=True, shortlist=shortlist,
                   caveats=[getattr(_class_module(class_name), "CAVEAT", MELEE_CAVEAT)])
    return payload


def report_from_dataset(dataset_path, class_name: str = "mage") -> dict[str, Any]:
    """Load a saved dataset (from `python -m wowforever update`) and build the report payload."""
    from pathlib import Path

    from wowforever.builds import load_builds
    from wowforever.schema import Dataset

    from wowforever.classes import class_module
    from wowforever.effects import attach_effects

    ds = Dataset.load(Path(dataset_path))
    # effects are the tool's reading of the rank text: re-derive them with the current rules,
    # so rule changes apply without refetching the game data
    module = class_module(class_name)
    cls, _ = attach_effects(ds.class_data(class_name), module.TALENT_EFFECTS, module.UNMODELED)
    meta = {"version": ds.version, "game_build": ds.game_build,
            "sources": [{"source": p.source, "game_build": p.game_build, "data_version": p.data_version,
                         "fetched_at": p.fetched_at} for p in ds.provenance]}
    builds = load_builds(class_name=class_name)
    if getattr(module, "ENGINE", False) in ("melee", "spell"):
        return melee_report(class_name, cls, builds, meta, hybrids=getattr(module, "HYBRIDS", ()))
    if not getattr(module, "ENGINE", False):
        return route_report(cls, builds, meta, hybrids=getattr(module, "HYBRIDS", ()),
                            scoring_note=getattr(module, "SCORING_NOTE", ""))
    return {"class": class_name, "engine": True,
            **build_report(cls, cls.spells, builds, StatTable.load(class_name), Assumptions.load(), meta)}
