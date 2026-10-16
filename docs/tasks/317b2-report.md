# Task #317, part B2: the report uses one PvE score and one stat table call

Make `tests/test_one_pve_score.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests. Edit only `src/wowforever/report.py`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Part B1 already removed `focus.pve_score_fn`, `focus.pvp_score_fn` and `PVE_REFERENCES`, so `report.py` fails at import right now; that is what you fix.
- Don't re-check things this spec states; read only `report.py`.

## Steps (all in `src/wowforever/report.py`)
1. The import line `from wowforever.focus import class_pvp_score, pve_score_fn, pvp_score_fn` becomes `from wowforever.focus import class_pvp_score`.
2. `shortlist_payload` (used only for the mage): its `fns` dict currently calls `pvp_score_fn(...)` and `pve_score_fn(...)`. Make them lambdas over `ranks`, as `melee_report` does for other classes:
   - `"PvP": lambda ranks: class_pvp_score("mage", stats_60, cls, ranks, kits, consensus)`, with `kits = load_kits()` loaded once before the dict
   - `"PvE": lambda ranks: ms.pve_score("mage", stats_60, cls.spells, cls, ranks)`, with `from wowforever import melee_scenarios as ms` at the top of the function
3. `report_from_dataset`: `stats_60 = StatTable.load("mage").at(60) if class_name == "mage" else (ms.stat_table(class_name).at(60) if getattr(module, "ENGINE", False) else None)` becomes `stats_60 = ms.stat_table(class_name).at(60) if getattr(module, "ENGINE", False) else None`.
4. `add_leveling`: `table = StatTable.load("mage") if class_name == "mage" else ms.stat_table(class_name)` becomes `table = ms.stat_table(class_name)`.
5. `add_stat_weights`: delete the `if class_name == "mage":` branch (its three lines). The `elif getattr(module, "ENGINE", False) in ("melee", "spell"):` becomes `if getattr(module, "ENGINE", False):`. In the `melee_build=` lambda further down, remove `class_name != "mage"` and the `and` joining it.

## Done when
- `tests/test_one_pve_score.py` passes: 7 tests.
- The fast suite passes.
