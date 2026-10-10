# Task #241: one changelog section per build, date and note

Make `tests/test_changelog_sections.py` pass without breaking the rest of the suite. Edit `src/wowforever/revisions.py` and `data/CHANGELOG.md` only. Do not edit the tests.

## Why
`wowforever update` checks each class on its own and calls `append_changelog` once per class, so one build's check writes a `## <build> (<date>)` heading per class: `data/CHANGELOG.md` has six identical 1.60.1.70291 headings.

## Changelog format
`# Data changelog\n`, then newest-first sections, each `\n## <build> (<date>)\n\n`, an optional note paragraph (lines starting `> `, then a blank line), then `- <line>\n` items. A section with no changes has the single item `- No talent or spell changes.`

## 1. `append_changelog(path, build, changes, *, date)`
Same signature. When the newest section has the heading `## {build} ({date})` and **no note**, merge into it instead of adding a heading: the union of its items and the new ones, sorted, without duplicates. `- No talent or spell changes.` is kept only when there's no other item. Otherwise (different build or date, an annotated newest section, or an empty changelog) insert a new section at the top as today.

## 2. New `collapse_changelog(text: str) -> str`
Merge every section with the same heading and the same note (no note counts as one value) into the first one of them, at the first one's position, with the same item rule as above. The header and section order otherwise stay the same. Raise `ValueError` if `text` doesn't start with the header, like `append_changelog`. Write a small private section parser and use it in both functions.

## 3. `data/CHANGELOG.md`
Rewrite it once with `collapse_changelog` (a one-off `.venv/Scripts/python -c` call is fine; don't add a script file). `test_repo_changelog_is_collapsed` checks it.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_changelog_sections.py` fails with `ImportError` on `collapse_changelog`. That's the expected failure; implementing it is the task. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Start with `revisions.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_changelog_sections.py tests/test_revisions.py`, then run the full suite once at the end (it takes over 10 minutes). If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
