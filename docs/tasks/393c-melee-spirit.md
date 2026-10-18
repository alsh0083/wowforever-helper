# Task #393/#399 (part A): Spirit on the melee stat rows

Make `tests/test_melee_spirit.py` pass. The test `test_tables_carry_spirit` needs the CSVs regenerated, which Claude
does after this task, so it is expected to still fail when you finish; the other two tests must pass. Do not edit
the tests and do not run `gear-stats`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/melee_stats.py`, then `src/wowforever/melee_scenarios.py`. Run the test file,
  then the fast suite once; no other test may fail.

## Why
The hunter's and paladin's mana regen talents (Bestial Discipline, Rapid Recuperation, Reverence) need Spirit, but
the melee stat rows drop it. The base files (`config/stats/<class>_base.csv`) carry it and gear can add it.

## Step 1: `src/wowforever/melee_stats.py`
1. In `class MeleeStats`, add as the last field (after `ranged: ...`):
   `    spirit: float = 0.0                         # base + gear (#393, #399)`
2. In `melee_stat_table`, in the `rows.append(MeleeStats(...))` call, add `spirit=base["spirit"] + totals.get("spirit", 0),`
   right after `main_hand=main, off_hand=off, ranged=ranged,`.
3. `COLUMNS` gains `"spirit"` as its last entry (after `"ranged_speed"`).
4. In `write_melee_csv`, the `values = [...]` list gains `r.spirit` as its last item (after `*weapons`).

## Step 2: `src/wowforever/melee_scenarios.py`, `MeleeStatTable.at`
The line
`        plain = {f.name: row[f.name] for f in fields(MeleeStats) if f.name not in WEAPON_COLUMNS and f.name != "level"}`
becomes
```python
        plain = {f.name: row.get(f.name, 0.0) for f in fields(MeleeStats)
                 if f.name not in WEAPON_COLUMNS and f.name != "level"}      # older tables have no spirit column
```

Nothing else changes.

## Done when
- `test_meleestats_has_spirit_with_a_default` and `test_a_table_without_the_column_reads_zero` pass; the rest of the
  fast suite has no new failures.
