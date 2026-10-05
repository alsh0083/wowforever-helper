# Task #28: archetype shortlist

Implement `src/wowforever/shortlist.py` so `tests/test_shortlist.py` passes. Do not edit tests. Standard library only, type hints, short docstrings. Uses `wowforever.rules.check_build`, `wowforever.builds.Build`, `wowforever.schema`.

Owner decisions (#28): per **archetype x focus** slots; each slot's default is the **community standard** build; a model-found variant is shown beside it only if it beats the standard by more than `margin` (5%) and is marked unproven; hand-written builds (the owner's Elementalist) appear only if they qualify; no fixed cap.

## `classify(cls, final, *, deep, hybrid, recognized) -> str | None`
Points per tree from `final` (talent id -> rank). If a tree has >= `deep` points: `"deep <tree name>"`. Else if exactly two trees have >= `hybrid` points: `"<A>/<B>"` with the two tree names **in tree order** (tree_id ascending); return it only if it is in `recognized`, else None. Otherwise None.

## `improve(cls, start, score_fn, *, archetype, deep, hybrid, recognized, max_evals=400) -> tuple[dict[int, int], float]`
Deterministic first-improvement hill climb over single-point moves:
- A move takes 1 point from talent `a` (rank > 0) and gives it to talent `b` (rank < max), `a != b`; iterate `a` and `b` by ascending talent id.
- A move is valid when the result passes `check_build(cls, result, level=cls.rules.max_level)` and `classify(...) == archetype`.
- Evaluate `score_fn(result)` (each call counts toward `max_evals`, and so does the initial `score_fn(start)`); take the **first** move that strictly improves the score, then restart the scan from that build. Stop when a full scan finds no improvement or the budget is spent.
- Return (best build, its score).

## `@dataclass(frozen=True) Slot`
`archetype, focus, standard: str | None, standard_score: float | None, model_pick: dict[int, int] | None, model_pick_score: float | None, candidates: dict[str, float]` (build id -> score, including the standard), `qualifying: tuple[str, ...]`; `as_dict()` -> JSON-friendly dict (talent ids as strings in `model_pick`).

## `build_shortlist(cls, builds, score_fns, *, margin, deep, hybrid, recognized, max_evals=400) -> list[Slot]`
- Slots: every tree as `"deep <name>"` plus every recognized hybrid, each x focus in `("PvP", "PvE")`, ordered by archetype as listed then PvP before PvE.
- For each build: `ids = build.final_ids(cls)`, archetype = classify(...). A build is a candidate of slot (archetype, build.variant), scored with `score_fns[focus](ids)`.
- **standard** = the slot's candidate with `origin == "community"` (highest score if several); its score = `standard_score`.
- **seed** for the search = the standard's build; if none, the best-scoring candidate of the slot; if none, the best-scoring build of the same archetype in the other focus (scored with this focus' function); if none, the slot stays empty (no model pick).
- **model pick** = `improve(seed...)`; kept only if its score > `(standard_score or seed score) * (1 + margin)`. With no standard, any strict improvement over the seed is kept.
- **qualifying** = the standard (if any) plus candidates with score >= `(1 - margin) * best`, where best = the highest score among the standard and candidates (not the model pick); ids sorted.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
