# Task #31: in-game test checklist (Python part)

Make `tests/test_checklist.py` pass without breaking the rest of the suite. Edit `config/assumptions.toml`, `src/wowforever/assumptions.py`, `src/wowforever/update.py`, `src/wowforever/report.py`, and create `src/wowforever/checklist.py`. Do not edit the tests. Claude does the dashboard part.

## Why
The unknown mechanics in `config/assumptions.toml` are what the owner will test in game once playing. Each needs to show as a checklist item, record a result when tested, and be flagged for a retest when a patch changes a talent or spell it involves.

## 1. Config and `Assumption`
- Each `[entry]` in `config/assumptions.toml` gets `talents = [...]`: the talent or spell names whose change should trigger a retest. Use these values:
  - frostfire_periodic_can_crit = ["Frostfire Bolt"]
  - frostfire_ticks_trigger_impact = ["Frostfire Bolt", "Impact"]
  - burning_soul_protects_frostfire = ["Frostfire Bolt", "Burning Soul"]
  - frostfire_interrupt_lockout = ["Frostfire Bolt"]
  - fingers_of_frost_applies_to_frostfire = ["Frostfire Bolt", "Fingers of Frost"]
  - aoe_target_cap = ["Blizzard", "Flamestrike", "Arcane Explosion", "Cone of Cold", "Blast Wave"]
  - sub20_spell_penalty = ["Frostbolt", "Fireball"]
- `Assumption` gains `talents: tuple[str, ...] = ()` read from that key (missing key -> `()`), keeping the field order so existing positional construction still works (append it after `tested`).

## 2. `src/wowforever/checklist.py`
```python
@dataclass(frozen=True)
class ChecklistItem:
    name: str          # assumption name
    question: str      # the assumption's `why`
    assumed: Any       # current value
    options: tuple[Any, ...]
    talents: tuple[str, ...]
    status: str        # "untested" | "tested" | "retest"
    result: str        # the `tested` text ("" when untested)

def checklist(assumptions: Assumptions, changes: Sequence[Change] = ()) -> list[ChecklistItem]
```
One item per assumption, in config order. Status: "untested" when `tested` is empty; "tested" when it isn't and no change touches the item; "retest" when it is tested and some `Change.talent` (case-insensitive) is in its `talents`. Untested items stay "untested" even when touched.

`retest_names(assumptions, changes) -> list[str]`: names of the "retest" items.

## 3. Update summary
`UpdateSummary` gains `retest: list[str] = field(default_factory=list)`, filled in `check_for_updates` with `retest_names(Assumptions.load(), changes)`. `text()` adds the line `Retest in game: a, b` when non-empty.

## 4. Report payload
`build_report` adds `"checklist": [asdict(item) for item in checklist(assumptions)]` (tuples become lists).

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_checklist.py` fails with `ModuleNotFoundError: No module named 'wowforever.checklist'`: that is the expected failure, and creating the module is the task. Install nothing and ask for no elevation. Write new files and edits with `tools/apply_patch.py` (see AGENTS.md). Start with `src/wowforever/checklist.py`; iterate with `.venv/Scripts/python -m pytest tests/test_checklist.py tests/test_assumptions.py`, then run the full suite once at the end.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
