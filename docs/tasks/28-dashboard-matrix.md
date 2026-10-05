# Task #28 view (+ #41 pairs, #30 save warnings): the spec matrix

Edit `dashboard/template.html` (and only the build-button code in `src/wowforever/dashboard.py` if needed) so `tests/test_dashboard_matrix.py` and the existing dashboard tests pass. Do not edit tests or the payload fixture. Plain JS/CSS, no frameworks, no external resources. Keep the existing visual identity: tokens `--bg`, `--panel`, `--gold`, `--frost`, `--fire`, `--arcane`, Georgia for headings/numbers, system sans for body.

## 1. Spec matrix (replaces the flat build-button row)
A section `<section id="spec-matrix">` right under the hero, rendered from `PAYLOAD.shortlist` (list of slots `{archetype, focus, standard, standard_score, model_pick, model_pick_score, model_pick_changes, model_pick_seed, candidates, qualifying}`) and `PAYLOAD.builds` (each has `id, name, variant, pair, origin`).

- A table-like grid: one **row per archetype** (in payload order), two columns **PvP** and **PvE**. Column headers in sentence case ("PvP", "PvE"). No uppercase eyebrows anywhere in this section.
- **Row label**: the archetype name with a left bar coloured by school: `deep Frost` → `--frost`, `deep Fire` → `--fire`, `deep Arcane` → `--arcane`; hybrids blend their two schools, e.g. `<div class="arch" data-archetype="Fire/Frost" style="--from:var(--frost);--to:var(--fire)">` with the bar drawn as a vertical gradient from `--from` to `--to`. Order of the two schools = the order in the archetype name mapped Arcane/Fire/Frost; for "Fire/Frost" that's `--from:var(--frost);--to:var(--fire)` (Frost first: it's the leveling foundation of the route) and for "Arcane/Fire" `--from:var(--arcane);--to:var(--fire)`.
- **Cell** `<div class="slot" data-slot="<archetype>|<focus>">` in exactly the payload order (the test reads them in document order). Contents:
  - the **standard**: build name (button that selects the build for the tracker), its score with 2 decimals, and the caption "Community standard"; if `standard` is null: the muted text "No community standard yet".
  - **qualifying** builds other than the standard: name button + score; builds whose `origin` is "hand" get a small "Yours" tag.
  - **model pick** (if present): "Model pick, unproven" + the gain over the standard (or over the seed when there's no standard) as a percentage, and a `<details>` listing `model_pick_changes` as "Talent from → to" lines (use the words, e.g. "Combustion 1 → 0"). Model picks are not selectable (they have no leveling order).
- Selecting a build highlights its button (gold border) and updates the tracker below (reuse the existing build-switch logic; keep `data-build="<id>"` on the buttons, the existing tests rely on it).

## 2. Pairs (#41)
In the selected-build panel, if another build shares its `pair` id, show "Pairs with <name> (<variant>)" as a button that switches to it.

## 3. Save versioning and patch warnings (#30)
- New per-build save key `wow-forever-save-v5-<build id>` storing `{level, checks: {<level>: {"talent": <name>, "rank": <n>}}}`. The `elementalist-v4` build still reads its old saves (`wow-forever-elementalist-v4` and the existing v1–v3 migration) once and converts them.
- On load, compare each saved check with the build's current order: if the talent/rank at that level still matches, keep it; otherwise **carry it over** to the level where that talent reaches that rank in the current order (if any). Show a notice in the tracker panel: "This build changed since your last visit: N checks carried over to new levels, M couldn't be carried over (talent removed or rank no longer in the build)." with a dismiss button. No notice when nothing changed.

## Done when
`.venv/Scripts/python -m pytest` passes in full. Claude will review the page visually.
