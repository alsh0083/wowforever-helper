# Task #366: the patch-readiness command

Make `tests/test_patch_readiness.py` and `tests/test_update.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests. `docs/patch-update.md` is already written.

This task has no reference code to copy: you write the implementation.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Make the edits before running any tests; then run the two test files, then the fast suite once.
- Before you start, `tests/test_patch_readiness.py` fails at import (`newest_saved_dataset` doesn't exist).
- Read only the files and functions named below. Don't re-check things this spec states.

## Why
When a game build lands, the model stays pinned to the old one (`config/dataset.toml`) until its logic catches
up. `patch-readiness` lists what still breaks on a saved build, so the work can be split per class and nothing
is forgotten (see `docs/patch-update.md`).

## Steps, in this order

### 1. `src/wowforever/schema.py`
Add `def newest_saved_dataset(datasets_dir: Path = DATASETS_DIR) -> Path:` right after `latest_dataset_path`. It
returns the saved dataset with the newest build, ignoring `config/dataset.toml`: the same glob and `max` as
`latest_dataset_path`, without the pin lines. Give it a one-line docstring.

### 2. `src/wowforever/readiness.py` (new)
Module docstring: patch readiness (#366), what still breaks if the model moves to a saved dataset's build.
`TABLES_DIR = <repo root> / "data" / "cache" / "wago"` (repo root = `Path(__file__).resolve().parents[2]`).

`def readiness(dataset_path: Path, *, tables_dir: Path | None = None) -> list[str]:` loads the dataset
(`Dataset.load`) and returns problem lines; it returns an empty list when everything is ready. For each class
name in `wowforever.classes.CLASSES`:
- `attach_effects(ds.class_data(name), module.TALENT_EFFECTS, module.UNMODELED)` (`module = class_module(name)`).
  Each line of its report becomes `f"{name}: effect rule: {line}"`.
- For each build in `load_builds(class_name=name)`:
  - if `b.unknown_talents(cls)` is non-empty, add `f"{name}: build {b.id}: unknown talents {', '.join(...)}"`
    and skip the rest for that build;
  - otherwise collect `check_build(cls, b.final_ids(cls), cls.rules.max_level)`;
  - when `b.order_ids(cls)` isn't None, add `check_order(cls, order)`'s lines, each prefixed `"order: "`;
  - each collected line becomes `f"{name}: build {b.id}: {line}"`.

Group buffs: `tables = tables_dir or TABLES_DIR / ds.game_build`.
- When `tables` doesn't exist, add exactly `f"group buffs: client tables not cached at {tables.name}, not checked"`.
- Otherwise run `group.build(read_tables(tables), group.talent_levels(ds, CLASSES), game_build=ds.game_build)`
  (`from wowforever import group`; `read_tables` from `wowforever.normalize`). Add
  `f"group buffs: {b['id']} doesn't resolve at 60"` for each buff in its `"buffs"` whose `by_level` has no `"60"`
  entry (treat a missing or None `by_level` as empty).

### 3. `src/wowforever/__main__.py`
- Add a subcommand `patch-readiness` (help: list what still breaks on a saved build before the model moves to it,
  #366) with `--dataset` (default: the newest saved dataset, via `newest_saved_dataset()`) and `--tables`
  (default: None).
- The handler prints each problem line, or "ready: nothing open", and returns 1 when there are problems, else 0.
  Follow the other handlers' style (imports inside the `if args.command == ...:` block).

### 4. `src/wowforever/update.py`
In `UpdateSummary.text()`, when `self.changed` is true, append as the last line:
`"Next: wowforever patch-readiness, then docs/patch-update.md"`.

## Done when
- `tests/test_patch_readiness.py` (6 tests) and `tests/test_update.py` pass.
- The fast suite has no new failures.
