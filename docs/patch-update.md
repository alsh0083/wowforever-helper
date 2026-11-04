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
- Rules first: each class's effect rules for the new rank text, checked against the saved dataset
  (`tests/test_rules_<build>.py`), before the pin moves.
- Then replace the builds, never repair them (owner, 2026-10-31, #460):
  1. `tools/import_sourced_builds.py`: deletes each class's non-hand builds and writes one community standard per
     slot from a current source (wowforeverbuilds.com's spec guide when its guard keeps it, then talentsforever.com's
     most saved complete top build). A source build naming a missing talent is left out, not adjusted.
  2. `tools/seed_tree_builds.py`: a PvE model build for each deep tree no source covers. The opponent kits play
     their tree's build and every report needs them.
  3. Every class report, then `tools/derive_slot_builds.py` (PvP slots), the reports again,
     `tools/derive_model_picks.py`, and `tools/derive_leveling_builds.py <class ...>`.
  4. `tools/derive_opponent_kits.py` re-derives the kits' level-60 health and DPS.
- Put renamed talents in `config/talent_renames.toml`.
## 4. Class work
- Golden tests come first. Each new or changed mechanic gets a hand-worked value in `tests/test_<build>_*.py`.
- Rules should match both the old fixture text and the new where that's easy. Tests that check "every rule
  parses" read the pinned dataset, not old fixtures.
- After each class merges into the integration branch:
  - re-derive the opponent kits (`tools/derive_opponent_kits.py`);
  - re-pin the dungeon regression values in `tests/test_dungeon_mana.py`;
  - list every re-pinned value as old → new in the PR. Re-pinned values are consistency checks, not proof.

## 5. Keep checking while the meta settles
Post-patch sources fill in over days: guides move to the new calculator, and top builds collect saves. Each time the
owner asks for an update check in the weeks after a patch, rerun step 3's import and derive tools. A slot whose source
now publishes a build takes it, and a guide whose tree or rank text still differs from ours stays out.
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
