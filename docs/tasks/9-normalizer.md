# Task #9: normalizer (talent structure + text)

Implement `src/wowforever/normalize.py` so `tests/test_normalize.py` passes. Do not edit tests, fixtures, `schema.py` or `classes/`.

## Background
Forever's talent trees live in the client's **Trait** tables, not the legacy `Talent` table (which is stale). One trait tree holds all three trees of a class side by side; `wowforever.classes.<class>.LAYOUT` (a `TraitLayout`) says how to cut it. Rank text and Classic comparisons come from wowforevertalent.com (`WftPage` from `wowforever.sources.wowforevertalent`).

## Interface
- `read_tables(directory: Path) -> dict[str, list[dict[str, str]]]`: every `*.csv` in the directory, keyed by file stem, rows as `csv.DictReader` dicts (UTF-8).
- `@dataclass NormalizeReport`: `build_mismatch: str | None`, `unmatched_wago: list[str]`, `unmatched_wft: list[str]`, `name_mismatches: list[str]`; property `ok` = no mismatch and all lists empty.
- `normalize_class(tables, layout: TraitLayout, page: WftPage, *, wago_build: str) -> tuple[ClassData, NormalizeReport]`

## Rules
1. **Nodes:** `TraitNode` rows with `TraitTreeID == layout.trait_tree_id`. Each node's entry is found via `TraitNodeXTraitNodeEntry` → `TraitNodeEntry` (`MaxRanks`) → `TraitDefinition` (`SpellID`) → `SpellName` (`Name_lang`). A node with more than one entry is a choice node: raise `ValueError` (none exist yet).
2. **Tree:** the band in `layout.trees` with the largest `min_x <= PosX`. **col** = `(PosX - band.min_x) // grid`, **row** = `(PosY - first_row_y) // grid`; if either isn't an exact multiple, raise `ValueError`.
3. **Talent:** `talent_id = int(node ID)`, `spell_id = int(SpellID)`, `rank_spell_ids = ()`, `name` from SpellName.
4. **Prerequisites:** each `TraitEdge` whose nodes are both in the tree: the right node requires the left node at the left node's **max rank**.
5. **Join with wowforevertalent.com:** for each talent, find the page talent in the tree with the same `name` as the band (`page.trees[i]["name"]`) at `row == row + 1` and `col == col + 1` (the page is 1-indexed).
   - If found and names match (case-insensitive): `rank_text` = the page's `ranks[*].text` in rank order, `classic_status` = `classic.status` if it's in `schema.CLASSIC_STATUS` else None, `icon` = page `icon`.
   - If found with a different name: leave text/status/icon empty and add `"<tree>/<wago name>: wowforevertalent.com has <page name>"` to `name_mismatches`.
   - If not found: leave empty and add `"<tree>/<name>"` to `unmatched_wago`.
   - Page talents never matched → `unmatched_wft` as `"<tree>/<name>"`.
6. **Trees:** `Tree(band.tree_id, band.name, talent ids sorted by (row, col))`, in band order. `ClassData(layout.class_name, trees, talents, rules=Rules())`.
7. **Build check:** if `page.game_build != wago_build`, set `build_mismatch` to a sentence containing both builds.

Standard library only, type hints, short docstrings.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
