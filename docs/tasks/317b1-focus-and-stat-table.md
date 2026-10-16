# Task #317, part B1: drop the mage-only score functions; stat_table serves the mage

Make these two tests pass:
`.venv/Scripts/python -m pytest tests/test_one_pve_score.py -k "gone or stat_table_serves"`.
Do not edit the tests. Edit only `src/wowforever/melee_scenarios.py` and `src/wowforever/focus.py`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Don't re-check things this spec states; read only the two files.
- `report.py` still imports the functions you delete, so other tests break until part B2. Run only the command above.

## Steps
1. `melee_scenarios.stat_table`: the branch for `getattr(module, "ENGINE", None) == "spell"` must also
   take the value `True` (the mage's module sets `ENGINE = True`). Use `in ("spell", True)`, with a comment
   saying `True` is the mage's own engine.
2. `focus.py`: delete the functions `pvp_score_fn` and `pve_score_fn`, the constant `PVE_REFERENCES`
   and the alias `ScoreFn`. Then remove the imports nothing in the file uses any more: `group`,
   `Assumptions`, `duel_side`, the `wowforever.scenarios` import, `Stats`, and `Callable`.
3. In `focus.py`'s module docstring, replace the PvE bullet with: PvE is `melee_scenarios.pve_score`,
   the same for every class (#317). In `class_pvp_score`'s docstring, change "Any other class's" to "Any class's".
