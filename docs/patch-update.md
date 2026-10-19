# When a new game build lands

The model reads one game build at a time: the one `config/dataset.toml` pins. A new build is saved as soon as an
update check finds it, but the model moves to it only once every class's logic handles it. Until then every
score is a **pre-patch** score, so say so whenever you report numbers. Build 1.60.1.70425 (the Oct 15 beta notes,
#339, milestone `patch-70425`) is the worked example.

## 1. Check and save the build (owner asks)
- `.venv/Scripts/python -m wowforever update`. This writes the raw snapshots, `data/datasets/<build>.json`, the
  data `CHANGELOG.md` entry, and post-patch popularity data. Merge that alone as a data-only PR.
- Keep `config/dataset.toml` on the old build, and add a comment naming the tracking issue (the pin-lag test
  requires one).

## 2. See what the build breaks
- `.venv/Scripts/python -m wowforever patch-readiness --dataset data/datasets/<build>.json` lists:
  - effect rules that don't parse;
  - builds that name removed talents or break new caps and row rules;
  - group buffs that don't resolve.

  It exits non-zero while anything is open.
- Read the changelog entry for what readiness can't see: spell data changes (costs, cast times, coefficients,
  levels), new spells, and rank text that still parses but now means something else.

## 3. One integration branch, one issue per class
- Branch `patch-<build>` from main and move the pin to the new build there first.
- Open one issue per class (plus group buffs and any data bug) under a milestone named for the build.
- Fix the builds first, so the suite can collect:
  - final allocations go legal, with a comment in each build file saying what moved and why;
  - put renamed talents in `config/talent_renames.toml`;
  - re-derive leveling builds with `tools/derive_leveling_builds.py <class ...>`.
- Then `tools/refresh_community_builds.py` (#369) replaces hand-moved community points with post-patch player
  data where it exists.

## 4. Class work
- Golden tests come first. Each new or changed mechanic gets a hand-worked value in `tests/test_<build>_*.py`.
- Rules should match both the old fixture text and the new where that's easy. Tests that check "every rule
  parses" read the pinned dataset, not old fixtures.
- After each class merges into the integration branch:
  - re-derive the opponent kits (`tools/derive_opponent_kits.py`);
  - re-pin the dungeon regression values in `tests/test_dungeon_mana.py`;
  - list every re-pinned value as old → new in the PR. Re-pinned values are consistency checks, not proof.

## 5. Keep checking while the meta settles
Post-patch popularity data starts thin. Each time the owner asks for an update check in the weeks after a patch, also
run `tools/refresh_community_builds.py`. It reports each refreshed community build as **stable** (same player build as
last time), **moved** (rewrites it) or **settled** (20+ saves and unchanged, so the `provisional` mark goes). Re-derive
the leveling builds and regenerate the reports when anything was rewritten. Builds still marked `provisional` show as
"Community standard (provisional, N saves)" on the dashboard.

After a patch, fetch only post-patch logs: `.venv/Scripts/python -m wowforever foreverlogs-refresh --week 147`
(weeks from 2024-01-01; add `--day 1 --day 2` for single days), then compare with
`validate-logs --stats stats-w147` (repeat `--stats` to add slices up). A 429 waits 60 s and retries once.

## 6. Move the model
- `patch-readiness` is clean on the new build.
- Regenerate every class report and the dashboard (`wowforever report ...`, `wowforever dashboard`).
- Re-run `wowforever validate-logs` (and `--single-target`) and compare each spec's model/logs ratio before and
  after.
- The merge PR lists every class's score shifts, the re-pinned values, and the mechanics that only have regression
  pins. Score changes need the owner's approval.
- Merge the integration branch to main, which moves the pin, and close the tracking issue.
