# Task #341: show the PvP core-talent bonus as its own line

Make `tests/test_pvp_core_line.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation. The tests have the
expected values, and the steps below say what goes where.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing; the package and dataset are ready.
- Before you start, `tests/test_pvp_core_line.py` fails at import (`pvp_core_line` doesn't exist yet). Nothing else in the fast suite fails.
- Don't regenerate `data/report*.json` or `dashboard/index.html`; that happens after merge.
- Read only the files named below. Don't re-check things this spec states.

## Why
The PvP score adds `CONSENSUS_BONUS` (0.10) × the share of the class's community core PvP talents
the build takes (`focus.side_pvp_score`). The bonus is left out of the per-scenario rows so classes
compare fairly; the dashboard should show it on its own line.

## Steps, in this order

### 1. `src/wowforever/focus.py`: `pvp_core_line`
Add after `core_talent_ids`:

```python
def pvp_core_line(cls: ClassData, consensus: Consensus, class_name: str,
                  ranks: Mapping[int, int]) -> dict | None:
```

- The class's core talent names: `pvp_core_talents(consensus, class_name)`, keeping only names the class has (`any(t.name == n for t in cls.talents)`, as `core_talent_ids` does).
- No core talents: return `None`.
- Otherwise return `{"taken": [...], "missing": [...], "bonus": ...}`. The two lists hold names, sorted alphabetically. A talent is taken when `ranks.get(talent_id, 0) > 0`. `bonus` is `round(CONSENSUS_BONUS * len(taken) / total, 3)`.

### 2. `src/wowforever/report.py`: `add_pvp_core`
Add a function next to `add_stat_weights`:

```python
def add_pvp_core(class_name: str, cls: ClassData, report: dict[str, Any]) -> None:
```

For each entry in `report["builds"]`: ranks are `ranks_at(entry["order"], cls.rules.max_level, cls)`.
Set `entry["pvp_core"] = pvp_core_line(cls, Consensus.load(), class_name, ranks)` only when that's not `None`.
Load the consensus once, before the loop. Import `pvp_core_line` from `wowforever.focus` next to the existing focus import.
Then call `add_pvp_core(class_name, cls, report)` in `report_from_dataset`, right after `add_stat_weights(...)`.

### 3. `dashboard/template.html`: the line
In `function renderScores()` (around line 224), after the statement that sets
`$('score-tables').innerHTML`, add new lines (don't lengthen the existing long lines):
when `build.pvp_core` exists, append to `$('score-tables').innerHTML` a
`<p class="unit">` with the text
`Community PvP talents: <taken count>/<taken + missing count> taken, +<bonus> PvP score`
and a `title` attribute listing the missing talents (`Missing: A, B`, or `All taken`).
The test checks that the template contains `build.pvp_core` and `Community PvP talents`.

## Done when
- `tests/test_pvp_core_line.py` passes: 8 tests.
- The fast suite passes.
