# Task #361: percentage mana costs (PowerCostPct)

Make `tests/test_mana_cost_pct.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. The cached client tables are at `data/cache/wago/<build>/` (not in git, but present).
- Before you start, `tests/test_mana_cost_pct.py` fails (SpellRank has no `mana_cost_pct`). The fast suite has
  other failures for priest and shaman; they belong to other tasks.
- Spell costs change for a few spells, so some regression pins (`test_kit_stats.py`, `test_dungeon_mana.py`) may
  move. Claude re-derives those; any other new failure is yours to fix.
- Read only the files named below. Don't re-check things this spec states.

## Why
wago's `SpellPower` table gives some spells' mana cost as a percentage of the caster's **base mana**
(`PowerCostPct`, with `ManaCost` = 0). The importer reads only `ManaCost`, so Arcane Blast, Multi-Shot,
Judgement, Stormstrike and others cost nothing in the model. Base mana per level is already in
`config/stats/<class>_base.csv` (column `base_mana`). The model scores builds at max level, so the cost is
resolved with the base mana at the class's max level (60). The dataset keeps the raw percentage; the
resolution happens when a class is read from it.

## Steps, in this order

### 1. `src/wowforever/schema.py`
- `SpellRank`: add `mana_cost_pct: float = 0.0` right after `mana_cost`, with a comment: % of base mana, from
  SpellPower.PowerCostPct; `Dataset.class_data` resolves it into `mana_cost` (#361).
- `Dataset.class_data(class_name)`: return the class with its spells resolved. A spell with `mana_cost == 0`
  and `mana_cost_pct > 0` gets `mana_cost = round(mana_cost_pct / 100 * base)` (Python `round`), via
  `dataclasses.replace`. `base` is the `base_mana` value in the row of `config/stats/<class_name>_base.csv`
  whose `level` equals the class's `rules.max_level`. When the file doesn't exist, or `base` is 0, leave the
  spells unchanged. Read the CSV through a small helper cached with `functools.lru_cache` (the path sits next
  to `RENAMES_FILE`'s config folder: `config/stats/`). Don't change the dataset that `class_data` is called on:
  return a new `ClassData` (`dataclasses.replace(c, spells=...)`).

- Add `Dataset.saved_class(class_name)` right before `class_data`: the stored class exactly as saved
  (costs unresolved), raising `KeyError` like `class_data` when the class is missing. Docstring: what update
  diffs compare.

### 2. `src/wowforever/update.py`
The update check diffs the new data against the previous dataset. Where it reads the baseline class
(`baseline = baseline_ds.class_data(class_name)`), read `baseline_ds.saved_class(class_name)` instead;
otherwise every percentage-cost spell would show up as a change (`tests/test_update.py` checks this).

### 3. `src/wowforever/normalize_spells.py`
Where it reads `costs` from `indexes.powers` (around `mana_cost = costs.get(_POWER_MANA, 0)`), also read the
mana row's `PowerCostPct` as a float (0.0 when absent or empty) into `mana_cost_pct`, and pass it to the
`SpellRank(...)` call.

### 4. `tools/backfill_mana_cost_pct.py` (new), then run it
A script: `.venv/Scripts/python tools/backfill_mana_cost_pct.py <build> [<build> ...]`. For each build it reads
`data/cache/wago/<build>/SpellPower.csv` (with `csv.DictReader`) and collects `PowerCostPct` of rows whose
`PowerType` is `"0"` (mana) and whose `PowerCostPct` is non-zero, by `SpellID`. It loads
`data/datasets/<build>.json` **with `json`** (not `Dataset.load`, which would resolve costs), sets
`"mana_cost_pct"` on every spell dict of every class (that spell's percentage, else 0.0), and writes the file
back exactly as `Dataset.save` formats it: `json.dumps(data, indent=1, sort_keys=True) + "\n"`, UTF-8, `\n`
line endings. Module docstring: what it does and why (#361). Then run it once:
`.venv/Scripts/python tools/backfill_mana_cost_pct.py 1.60.1.70291 1.60.1.70425`.

## Done when
- `tests/test_mana_cost_pct.py` passes: 7 tests, and `tests/test_update.py` still passes.
- The fast suite has no new failures apart from moved regression pins.
