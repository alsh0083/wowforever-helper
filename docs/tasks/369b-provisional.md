# Task #369 follow-up: provisional community builds until the post-patch meta settles

Make `tests/test_community_provisional.py` and `tests/test_community_refresh.py` pass without breaking the rest of
the fast suite (`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. **Make the edits first**, then run the two test files, then the fast suite once.
- Edit `src/wowforever/community.py`, `src/wowforever/builds.py`, `src/wowforever/dashboard.py`,
  `src/wowforever/report.py` and `tools/refresh_community_builds.py`; at the end run the tool once with `--write`
  (step 5).
- Before you start, `tests/test_community_provisional.py` fails at import.

## Why
Right after a patch, wowforevertalent.com's post-patch popularity data is thin: some refreshed community builds
come from players' builds with 5-9 saves. The owner wants the refresh re-run on every update check until the top
builds stop moving. A refreshed build with fewer than 20 saves is **provisional**. Each refresh records which player
build it took (a signature of its talents), so the next refresh can tell whether the pick is stable or has moved.

## Steps, in this order

### 1. `src/wowforever/community.py`
- `PROVISIONAL_SAVES = 20`, with a one-line comment.
- `def final_signature(final: dict) -> str:` returns `",".join(f"{name}={rank}" for name, rank in sorted(final.items())
  if rank > 0)`.
- `refreshed_toml(text, entry, *, window, today)`: the new keyword `today` is a `YYYY-MM-DD` string.
  - Besides what it does now, remove any existing top-level line starting with `provisional =` or `refreshed =`,
    and any existing line starting with `# refreshed from`.
  - Then put these lines directly above the `# refreshed from ...` note it writes, in this order:
    `refreshed = "<rank>:<final_signature(entry["final"])>"`, and, only when `entry["saved"] < PROVISIONAL_SAVES`,
    `provisional = "<saved> saves, <today>"`.
- `def refresh_status(build, entry) -> str:`
  - When `build.refreshed` is empty, or its part after the first `:` differs from `final_signature(entry["final"])`,
    return `"moved"`.
  - Otherwise return `"settled"` when `entry["saved"] >= PROVISIONAL_SAVES`, else `"stable"`.

### 2. `src/wowforever/builds.py`
`Build`: two more last fields, `provisional: str = ""` (post-patch player data with few saves, #369) and
`refreshed: str = ""` (`"<popularity rank>:<signature>"` of the player build it was refreshed from, #369).
`Build.load` reads both with `raw.get(..., "")`.

### 3. `src/wowforever/dashboard.py` and `src/wowforever/report.py`
- `standard_caption`: before the `adjusted` check, a build with a non-empty `provisional` returns
  `f"Community standard (provisional, {provisional.split(' saves')[0]} saves)"`.
- `report.py`: the three build payload dicts that carry `"adjusted": b.adjusted` also get
  `"provisional": b.provisional`.

### 4. `tools/refresh_community_builds.py`
- Builds to look at: endgame community builds sourced from `wft_popular*` with a non-empty `adjusted`,
  `provisional` or `refreshed`, or whose file has a line starting with `# refreshed from` (refreshed before this
  task). Catalog plans keep today's "re-import it" line.
- Print `refresh_status(b, match)` on each build's row.
- With `--write`, rewrite when the status is `"moved"` or `"settled"`, passing `today=date.today().isoformat()`
  (`from datetime import date`). A settled rewrite drops `provisional`, because the match has 20+ saves.
- The `MIN_OVERLAP` check stays, for builds that are still `adjusted`.

### 5. Run it
`.venv/Scripts/python tools/refresh_community_builds.py --write`. This marks the builds refreshed in #369 with
`refreshed` and, under 20 saves, `provisional` (priest-shadow 5, warlock-affliction 9).

## Done when
- `tests/test_community_provisional.py` (6 tests) and `tests/test_community_refresh.py` pass.
- The fast suite has no new failures.
