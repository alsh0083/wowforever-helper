"""Archetype shortlist (#28).

Classifies builds into archetypes (a deep tree or a recognized hybrid) and, per
archetype x focus slot, compares the community standard against a model pick
found by hill climbing. Everything is class-agnostic: deep/hybrid thresholds
and the recognized hybrids are passed in.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from wowforever.builds import Build
from wowforever.rules import check_build
from wowforever.schema import ClassData

ScoreFn = Callable[[Mapping[int, int]], float]
_FOCUS_ORDER = ("PvP", "PvE")


def _tree_points(cls: ClassData, final: Mapping[int, int]) -> list[tuple[str, int]]:
    """(tree name, points in the tree) per tree, in tree order."""
    ordered = sorted(cls.trees, key=lambda tree: tree.tree_id)
    return [(tree.name, sum(final.get(tid, 0) for tid in tree.talent_ids)) for tree in ordered]


def classify(
    cls: ClassData,
    final: Mapping[int, int],
    *,
    deep: int,
    hybrid: int,
    recognized: tuple[str, ...],
) -> str | None:
    """Archetype label for a build: the deep tree, a recognized hybrid, or None."""
    points = _tree_points(cls, final)
    for name, total in points:
        if total >= deep:
            return f"deep {name}"
    hybrid_trees = [name for name, total in points if total >= hybrid]
    if len(hybrid_trees) == 2:
        label = "/".join(hybrid_trees)
        return label if label in recognized else None
    return None


def improve(
    cls: ClassData,
    start: Mapping[int, int],
    score_fn: ScoreFn,
    *,
    archetype: str,
    deep: int,
    hybrid: int,
    recognized: tuple[str, ...],
    max_evals: int = 400,
) -> tuple[dict[int, int], float]:
    """Deterministic first-improvement hill climb over single-point moves.

    A move shifts one point from talent a to talent b (both iterated in
    ascending talent id) and is kept only when the result is legal and stays
    in `archetype`. Every `score_fn` call, including the initial one, counts
    against `max_evals`; returns the best build found and its score.
    """
    max_rank = {talent.talent_id: talent.max_rank for talent in cls.talents}
    all_ids = sorted(max_rank)
    evals = 0

    def evaluate(ranks: Mapping[int, int]) -> float:
        nonlocal evals
        evals += 1
        return score_fn(ranks)

    best = {tid: rank for tid, rank in start.items() if rank > 0}
    best_score = evaluate(best)
    while evals < max_evals:
        improved = False
        for a in sorted(tid for tid, rank in best.items() if rank > 0):
            if improved or evals >= max_evals:
                break
            for b in all_ids:
                if evals >= max_evals:
                    break
                if b == a or best.get(b, 0) >= max_rank[b]:
                    continue
                result = dict(best)
                result[a] -= 1
                if result[a] == 0:
                    del result[a]
                result[b] = best.get(b, 0) + 1
                if check_build(cls, result, level=cls.rules.max_level):
                    continue
                if classify(cls, result, deep=deep, hybrid=hybrid, recognized=recognized) != archetype:
                    continue
                score = evaluate(result)
                if score > best_score:
                    best, best_score = result, score
                    improved = True
                    break
        if not improved:
            break
    return best, best_score


@dataclass(frozen=True)
class Slot:
    """One archetype x focus slot: community standard, model pick, and candidates."""

    archetype: str
    focus: str
    standard: str | None
    standard_score: float | None
    model_pick: dict[int, int] | None
    model_pick_score: float | None
    candidates: dict[str, float]
    qualifying: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """JSON-friendly view of the slot; talent ids in `model_pick` become strings."""
        pick = self.model_pick
        return {
            "archetype": self.archetype,
            "focus": self.focus,
            "standard": self.standard,
            "standard_score": self.standard_score,
            "model_pick": {str(tid): rank for tid, rank in pick.items()} if pick is not None else None,
            "model_pick_score": self.model_pick_score,
            "candidates": dict(self.candidates),
            "qualifying": list(self.qualifying),
        }


def build_shortlist(
    cls: ClassData,
    builds: list[Build],
    score_fns: Mapping[str, ScoreFn],
    *,
    margin: float,
    deep: int,
    hybrid: int,
    recognized: tuple[str, ...],
    max_evals: int = 400,
) -> list[Slot]:
    """One Slot per archetype x focus: community standard, model pick, candidates.

    Each build enters the slot (its archetype, its variant), scored with that
    focus' function. The standard is the best community candidate; the model
    pick starts from the standard, else the best candidate, else a same-
    archetype build of the other focus, and is kept only when it beats the
    standard by `margin` (or the seed itself, when there is no standard).
    """
    archetypes = [f"deep {tree.name}" for tree in sorted(cls.trees, key=lambda tree: tree.tree_id)]
    archetypes.extend(recognized)

    scored: list[tuple[Build, dict[int, int], str | None]] = []
    for build in builds:
        ids = build.final_ids(cls)
        scored.append((build, ids, classify(cls, ids, deep=deep, hybrid=hybrid, recognized=recognized)))

    candidates_by_slot: dict[tuple[str, str], list[tuple[Build, dict[int, int], float]]] = {
        key: [] for archetype in archetypes for key in ((archetype, focus) for focus in _FOCUS_ORDER)
    }
    for build, ids, archetype in scored:
        if archetype is None or build.variant not in score_fns:
            continue
        candidates_by_slot[(archetype, build.variant)].append((build, ids, score_fns[build.variant](ids)))

    slots: list[Slot] = []
    for archetype in archetypes:
        for focus in _FOCUS_ORDER:
            other_focus = "PvE" if focus == "PvP" else "PvP"
            score_fn = score_fns[focus]
            cands = candidates_by_slot[(archetype, focus)]
            community = [cand for cand in cands if cand[0].origin == "community"]
            standard = max(community, key=lambda cand: cand[2]) if community else None

            seed = standard
            if seed is None and cands:
                seed = max(cands, key=lambda cand: cand[2])
            if seed is None:
                cross = [
                    (build, ids, score_fn(ids))
                    for build, ids, arch in scored
                    if arch == archetype and build.variant == other_focus
                ]
                seed = max(cross, key=lambda cand: cand[2]) if cross else None

            model_pick: dict[int, int] | None = None
            model_pick_score: float | None = None
            if seed is not None:
                pick, pick_score = improve(
                    cls,
                    seed[1],
                    score_fn,
                    archetype=archetype,
                    deep=deep,
                    hybrid=hybrid,
                    recognized=recognized,
                    max_evals=max_evals,
                )
                keep_threshold = standard[2] * (1 + margin) if standard is not None else float(seed[2])
                if pick_score > keep_threshold:
                    model_pick, model_pick_score = pick, pick_score

            scores = [score for _, _, score in cands]
            if standard is not None:
                scores.append(standard[2])
            qualifying: list[str] = []
            if scores:
                qualify_threshold = (1 - margin) * max(scores)
                qualifying = [build.id for build, _, score in cands if score >= qualify_threshold]
                if standard is not None:
                    qualifying.append(standard[0].id)

            slots.append(
                Slot(
                    archetype,
                    focus,
                    standard[0].id if standard is not None else None,
                    standard[2] if standard is not None else None,
                    model_pick,
                    model_pick_score,
                    {build.id: score for build, _, score in cands},
                    tuple(sorted(set(qualifying))),
                )
            )
    return slots
