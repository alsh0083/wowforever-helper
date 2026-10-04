# Task #13: on-demand `check for updates` command

Implement `src/wowforever/update.py` and the `update` subcommand in `src/wowforever/__main__.py` so `tests/test_update.py` passes. Do not edit tests or fixtures. Standard library only, type hints, short docstrings.

Also add `SKILL_LINES = (6, 8, 237)` (Frost, Fire, Arcane) to `src/wowforever/classes/mage.py`.

## `check_for_updates(http_get, *, data_dir: Path, delay: float = 1.0, now: str | None = None) -> UpdateSummary`
Mage only for now. `now` defaults to the current UTC time (ISO 8601); use it for every timestamp.

1. Builds: `json.loads(http_get("https://wago.tools/api/builds"))` → `sources.wago.latest_build`.
2. wago: `sources.wago.fetch_build(build, http_get=http_get, cache_dir=data_dir/"cache"/"wago", manifest_dir=data_dir/"raw"/"wago", delay=delay)`.
3. wowforevertalent.com: `sources.wowforevertalent.fetch("mage", http_get=http_get, raw_dir=data_dir/"raw"/"wowforevertalent")`, then `parse_page` on the saved file.
4. Normalize: `read_tables(cache dir of the build)` → `normalize_class(tables, mage.LAYOUT, page, wago_build=build)` → `effects.attach_effects(cls, mage.TALENT_EFFECTS, mage.UNMODELED)` → `normalize_spells.class_spells(tables, skill_lines=mage.SKILL_LINES)`; put the spells on the class (`dataclasses.replace(cls, spells=spells)`).
5. Dataset: `Dataset(version=build, game_build=build, classes=(cls,), provenance=(…))` with one `Provenance` per source: wago (`game_build=build`, `data_version=build`, `snapshot_sha256` = sha256 of the manifest file's bytes) and wowforevertalent.com (`game_build=page.game_build`, `data_version=page.page_data_version`, `snapshot_sha256` from its manifest's `sha256`). `validate()` it.
6. Previous dataset: the highest build below `build` among `data_dir/"datasets"/*.json` (compare numeric version tuples). Changes = `revisions.diff_class` + `revisions.diff_spells` against it (no previous → no diff, but `changed = True`).
7. If changed: save the dataset to `data_dir/"datasets"/f"{build}.json"`; `append_changelog(data_dir/"CHANGELOG.md", build, changes, date=now[:10])`. If a dataset for `build` already exists and nothing changed, don't rewrite it.
8. `affected_builds(changes, builds.load_builds())`; `crosscheck(cls, page, report, wago_build=build)`; `record_check(data_dir/"builds.json", build, changed=…, dataset=<relative path or None>, checked_at=now)`.

`@dataclass UpdateSummary`: `build`, `previous_build: str | None`, `changed: bool`, `changes: list[Change]`, `affected_builds: list[str]`, `crosscheck: CrosscheckResult`, `effect_problems: list[str]`; `text()` → short chat-ready summary: the build, whether it changed (list up to 20 changes, then "and N more"; or "No talent or spell changes."), affected build ids, `crosscheck.summary()`, effect problems if any.

## CLI
`python -m wowforever update [--data-dir data] [--delay 1.0]` prints `summary.text()` and returns 0. It calls `check_for_updates(update.default_http_get, …)`, where `update.default_http_get` is a module attribute (set to `sources.http.http_get`) looked up **at call time** so tests can replace it.

## Done when
`.venv/Scripts/python -m pytest` passes in full (after #11/#12 are merged into this branch).
