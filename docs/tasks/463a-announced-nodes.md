# Task #463 (part A): read wowforevertalents.com's announced and latest talent nodes

Make `tests/test_wowforevertalents.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/sources/wowforevertalents.py`. No network.
- Before you start, `test_announced_and_latest_nodes_are_read_like_the_rest` fails; the other tests pass.
- Run `.venv/Scripts/python -m pytest tests/test_wowforevertalents.py -q` after the step, then the fast suite once.

## Why
Since 3 Nov the site writes talents from Blizzard's 2 Nov notes as `<div class="node is-announced" ...>` and recent
ones as `<div class="node is-latest" ...>`. `class_trees` splits cells only on `<div class="node" `, so it drops
them (rogue: 24 of 54 talents read), and `update` mixes the old and new trees.

## Step 1: `src/wowforever/sources/wowforevertalents.py`
Replace
```python
        for cell in re.split(r'(?=<div class="node" )', article)[1:]:
```
with
```python
        for cell in re.split(r'(?=<div class="node[ "])', article)[1:]:
```

## Done when
- `tests/test_wowforevertalents.py` passes; the fast suite has no other new failures.
- Only `src/wowforever/sources/wowforevertalents.py` changed.
