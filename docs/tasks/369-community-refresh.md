# Task #369: refresh hand-adjusted community builds from post-patch player data

Make `tests/test_community_refresh.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Make the edits before running any tests; then run the test file, then the fast suite once.
- Before you start, `tests/test_community_refresh.py` fails 4 of 5 tests. Don't run the new tool with `--write`;
  Claude runs it.
- Read only the files and functions named below. Don't re-check things this spec states.

## Why
Build 1.60.1.70425 removed and re-capped talents, so Claude moved points in 8 community builds by hand. Each of
those files now has a top-level `adjusted = "1.60.1.70425: <what moved>"` line, followed by `# 1.60.1.70425
(#353) ...` comment lines and then `[final]`. No player chose those points. `data/popularity/<class>.json` holds
the post-patch top builds from wowforevertalent.com. Its `"top"` is a list of dicts with int fields `rank`,
`saved`, a list `points`, and `final`, a dict of talent name to rank. This task replaces each adjusted build with the
closest real post-patch build, and labels the ones that stay adjusted.

## Steps, in this order

### 1. `src/wowforever/builds.py`
`Build`: add a last field `adjusted: str = ""`, with the comment: points moved by hand for a new build, with no
player behind them (#369). `Build.load` passes `raw.get("adjusted", "")`.

### 2. `src/wowforever/community.py` (new)
Module docstring: refreshing hand-adjusted community builds from post-patch popularity data (#369).
- `def closest_popular(build, cls, top) -> dict | None:`
  - The build's main tree is `melee_scenarios.main_tree(cls, build.final_ids(cls))`.
  - For each entry of `top`:
    - keep only its `final` talents that exist in `cls` (any talent with that name);
    - skip the entry unless `main_tree` of those ranks (by talent id) is the same tree;
    - its overlap is `sum(min(rank, build.final.get(name, 0)))` over its talents.
  - Return the entry with the highest overlap as a new dict, `{**entry, "overlap": overlap}` with `final` filtered
    as above. Break ties by the higher `saved`. With no entry left, return None.
- `def refreshed_toml(text: str, entry: dict, *, window: str) -> str:` rewrites a build file's text:
  - Remove the `adjusted = ...` line and every line after it up to (not including) the `[final]` line.
  - Replace the `[final]` table's body, every line after `[final]` up to the next line starting with `[` or the end
    of the file, with one `"<talent>" = <rank>` line per talent of `entry["final"]` whose rank is above 0, in the
    entry's order.
  - Put one comment line right above `[final]`:
    `# refreshed from wowforevertalent.com popularity (<window>): rank <rank>, saved <saved>, points <a>/<b>/<c> (#369)`.
    The points come from the list `entry["points"]`.
  - Everything else stays as it is.

### 3. `tools/refresh_community_builds.py` (new)
Usage: `.venv/Scripts/python tools/refresh_community_builds.py [--write]`. For every class in
`wowforever.classes.CLASSES`:
- load `data/popularity/<class>.json` (skip the class if it's missing) and the pinned dataset's class
  (`Dataset.load(latest_dataset_path()).class_data(c)`);
- for every build of that class with `mode == "endgame"`, `origin == "community"` and a non-empty `adjusted`, print
  one row: build id, the match's rank, saved count, points and overlap, or "no post-patch build in this tree";
- with `--write`, rewrite `config/builds/<id>.toml` with `refreshed_toml(..., window=<the file's "sourceWindow">)`
  when there is a match.

Module docstring: usage, and that leveling builds need re-deriving afterwards (`tools/derive_leveling_builds.py`).

### 4. Labels: `src/wowforever/report.py` and `src/wowforever/dashboard.py`
- `report.py`: the three build payload dicts that carry `"origin": b.origin` also get `"adjusted": b.adjusted`.
- `dashboard.py`: add a module-level function `standard_caption(build: dict) -> str`:
  - origin `"model"` returns "Model build, no community plan yet";
  - origin `"hand"` returns "Custom build, no community plan yet";
  - any other origin with a non-empty `adjusted` returns
    `f"Community standard, points adjusted for {adjusted.split(':')[0]}"`;
  - otherwise it returns "Community standard".

  In the slot rendering, the `{"model": ..., "hand": ...}.get(origin, "Community standard")` expression becomes
  `standard_caption(by_id.get(slot["standard"], {}))`.

## Done when
- `tests/test_community_refresh.py` passes: 5 tests.
- The fast suite has no new failures.
