# Tasks #11 and #12: revision tracking and cross-source check

Implement `src/wowforever/revisions.py` (#11) and `src/wowforever/crosscheck.py` (#12) so `tests/test_revisions.py` and `tests/test_crosscheck.py` pass. Do not edit tests or other modules. Standard library only, type hints, short docstrings.

## `revisions.py`

- `@dataclass(frozen=True) Change`: `scope` (tree name for talents, `""` for spells), `talent` (talent or spell name **before** the change), `kind` (`"added"`, `"removed"`, `"changed"`), `text`. `str(change)` is `"{scope}/{talent}: {text}"` for talents and `"{talent} rank {n}: {text}"` for spells (store the spell rank in the dataclass too).
- `diff_class(old: ClassData, new: ClassData) -> list[Change]`: match talents by `talent_id`. Texts:
  - new id → kind added, `"new talent"` (scope = tree in `new`); missing id → removed, `"removed"`
  - name differs → `"renamed to {new name}"`
  - `max_rank` differs → `"max rank {old} -> {new}"`
  - tree/row/col differs → `"moved from row {r} col {c} to row {r} col {c}"`, **1-indexed**
  - prerequisite differs → `"prerequisite {X} -> {Y}"`, where each side is `"{name} (rank {n})"` or `"none"`
  - `rank_text` differs → `"rank text changed"`
  - one Change per difference; a talent can produce several
- `diff_spells(old: Sequence[SpellRank], new: Sequence[SpellRank]) -> list[Change]`: match by `spell_id`; added → `"new spell rank"`, removed → `"removed"`, otherwise one Change per differing field (every dataclass field except `spell_id`, `name`, `rank`): `"{field} {old} -> {new}"` with plain `str()` of each value.
- `affected_builds(changes, builds: Sequence[Build]) -> list[str]`: ids (in input order) of builds naming any changed talent in `final`, `order` or `must_have_by` (compare names case-insensitively; for renames also check the new name).
- `append_changelog(path, build: str, changes, *, date: str)`: file starts with `# Data changelog\n`; each call inserts a section **right after the header** (newest first): `\n## {build} ({date})\n\n` followed by `- {str(change)}\n` per change, sorted, or `- No talent or spell changes.\n` when empty. Create the file if missing. UTF-8, `\n` newlines.
- `record_check(path, build, *, changed: bool, dataset: str | None, checked_at: str)`: JSON list of `{"build", "changed", "dataset", "checked_at"}`, one entry per build (re-checking a build replaces its entry in place), `indent=1`.

## `crosscheck.py`

- `@dataclass CrosscheckResult`: `lagging_source: str | None`, `builds: dict[str, str]` (source → build), `problems: list[str]`; property `ok` (no problems and no lag); `summary() -> str`: `"Sources agree."` when ok; otherwise one line per finding, starting with the lag (`"wowforevertalent.com is on build X; wago.tools is on build Y."`) when present.
- `crosscheck(cls: ClassData, page: WftPage, report: NormalizeReport, *, wago_build: str) -> CrosscheckResult`:
  - builds: `{"wago.tools": wago_build, "wowforevertalent.com": page.game_build}`; the source with the numerically lower build lags (none if equal)
  - problems: everything in `report.unmatched_wago`, `report.unmatched_wft`, `report.name_mismatches` (as given), plus, for every talent matched by tree name + 1-indexed row/col + name:
    - max rank differs: `"{tree}/{name}: max rank {wago} (wago.tools) vs {page} (wowforevertalent.com)"`
    - prerequisite differs (the page's `prerequisite` is a talent id like `"2-5-2"` = tree index 0-based, row, col 1-indexed; resolve it to a name in the page): `"{tree}/{name}: prerequisite {wago name or none} (wago.tools) vs {page name or none} (wowforevertalent.com)"`

## Done when
`.venv/Scripts/python -m pytest` passes in full.
