# Task #317, part B: one PvE score, one stat table call

Make `tests/test_one_pve_score.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation. The steps below say what
goes where.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing; the package and dataset are ready.
- Before you start, 3 tests in `tests/test_one_pve_score.py` fail (the mage-only functions still exist, `stat_table("mage")` loads the wrong table, `report.py` has a mage branch). `tests/test_focus.py` already uses the new calls.
- Read only the files and functions named below. Don't re-check things this spec states.

## Why
Part A made `melee_scenarios.raid` give the mage's raid exactly. The mage can now use the PvE
score and the PvP score every other class uses, so the mage-only versions go.

## Steps, in this order

### 1. `src/wowforever/melee_scenarios.py`: `stat_table`
It loads the caster table when the module's `ENGINE == "spell"`. The mage's module has `ENGINE = True`.
Make the caster branch also take `True`, with a short comment that `True` is the mage's own engine.

### 2. `src/wowforever/focus.py`
- Delete `pvp_score_fn`, `pve_score_fn` and `PVE_REFERENCES` (the shared references are in `config/melee_scenarios.toml` `[references]`).
- Delete `ScoreFn` and every import nothing uses any more. `shortlist.py` has its own `ScoreFn`.
- Fix the module docstring's PvE bullet: the PvE score is now `melee_scenarios.pve_score`, the same for every class.
- `class_pvp_score`'s docstring says "Any other class's": make it "Any class's".

### 3. `src/wowforever/report.py`
- Import only `class_pvp_score` from `wowforever.focus`.
- `shortlist_payload` (mage only): its two score functions become lambdas over `ranks`, as `melee_report` does:
  `class_pvp_score("mage", stats_60, cls, ranks, kits, consensus)` with `kits = load_kits()` loaded once, and
  `ms.pve_score("mage", stats_60, cls.spells, cls, ranks)`. Import `melee_scenarios as ms` inside the function.
- `report_from_dataset`: `stats_60` comes from `ms.stat_table(class_name).at(60)` whenever the module has an `ENGINE`, mage included (one expression, no `class_name == "mage"`).
- `add_leveling`: `table = ms.stat_table(class_name)` for every class.
- `add_stat_weights`: the `if class_name == "mage":` branch goes. The branch that remains handles every class whose module has a truthy `ENGINE`. In the `melee_build=` lambda, drop `class_name != "mage" and`: the mage's playstyle is "caster".
- Afterwards no `StatTable.load("mage")` may remain in `report.py` (the test checks this). The one `StatTable.load(class_name)` in the mage's `build_report` call may stay.

## Done when
- `tests/test_one_pve_score.py` passes: 7 tests.
- The fast suite passes.
