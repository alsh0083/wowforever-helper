# Task #22: dashboard generator with build switcher

Make `tests/test_dashboard.py` pass and turn the hand-written `dashboard/index.html` into a generated page. Do not edit tests or the payload fixture.

## Files
- `dashboard/template.html`: **start from the current `dashboard/index.html`** and keep its look and features: header crest, level slider/field, milestone buttons, timeline of points with rank check-off buttons, the next-point panel, Frost/Fire progress, localStorage progress with try/catch, reset with confirmation, the responsive layout. Replace the hard-coded `talents`, `talentImages`, `milestones` and migration data with two placeholders on their own lines:
  - `const PAYLOAD = /*__PAYLOAD__*/null;`
  - `const ICONS = /*__ICONS__*/{};` (icon name → `data:image/jpeg;base64,...`)
- `src/wowforever/dashboard.py`:
  - `render(payload: dict, icons: dict[str, bytes]) -> str`: reads the template, replaces `/*__PAYLOAD__*/null` with `json.dumps(payload)` and `/*__ICONS__*/{}` with the data-URI map, and returns the HTML. The result must contain the line `const PAYLOAD = {...};` exactly as the test's regex expects.
  - `fetch_icons(names, *, http_get_bytes, cache_dir: Path) -> dict[str, bytes]`: for each unique non-empty name, read `cache_dir/<name>.jpg` if present, else GET `https://wowforevertalent.com/assets/icons/<name>.jpg` and cache it.
  - Add `http_get_bytes(url) -> bytes` to `src/wowforever/sources/http.py` (same User-Agent/timeout as `http_get`).
- CLI in `__main__.py`: `python -m wowforever dashboard [--report data/report.json] [--out dashboard/index.html]` loads the report JSON, fetches icons for every talent in it (cache `data/cache/icons`), renders, writes UTF-8.

## Page behavior (all from `PAYLOAD`, plain JS, no external resources)
- **Build switcher**: one button per build with `data-build="<id>"` and the build's `name`; selection remembered in localStorage (`wow-forever-selected-build`).
- For the selected build: `summary`, `gives_up`, `order_source`, open points (if any), the point timeline from `order` (talent id per point, first point at `rules.first_talent_level`; group consecutive points of the same talent like today), each talent's icon (`ICONS[talents[id].icon]`), name, tree, and current/next rank text on hover or in the next-point panel.
- **Milestones** row: the build's `must_have_by` talents at their levels (replaces the hard-coded Ice Block 25 / Cold Snap 30 / ... list).
- **Scores** panel: a small table per scenario (`questing`, `aoe`, `raid`) for the selected build at the checkpoint levels with unit and spell; mark the best build at each level. Under it, the build's `sensitivity` notes and the payload `caveats`.
- **Spell training**: the `spell_milestones` up to the current level, next few highlighted.
- **Progress per build** in localStorage key `wow-forever-<build id>`; checks are keyed by level like today. The `elementalist-v4` build must keep using `wow-forever-elementalist-v4` and the existing migration from older versions so current saves still load.
- **Footer**: dataset `game_build` and `version`, "Talent text and icons: wowforevertalent.com (Creative Commons Attribution)", "Game data: wago.tools".

## Done when
`.venv/Scripts/python -m pytest` passes. Don't fetch anything from the network yourself (icons are fetched by the CLI when Claude runs it). Keep the JS readable; no frameworks.
