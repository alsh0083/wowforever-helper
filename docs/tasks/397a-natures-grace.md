# Task #397 (part 1): Nature's Grace

Make `tests/test_natures_grace.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/caster.py` first, then `src/wowforever/classes/druid.py`. Run the test file,
  then the fast suite once. Druid regression pins (`tests/test_kit_stats.py`, opponent kits) may move; Claude
  re-derives them.
- Before you start, most tests in `tests/test_natures_grace.py` fail.

## Why
Nature's Grace: a spell crit makes the next cast and its global cooldown 10% faster. On average every cast is
faster by (crit chance x 10%), best effort (owner OK 2026-10-16). A new effect kind `crit_haste_pct` carries it.

## Step 1: `src/wowforever/caster.py`, `cast`
Directly after the two lines
```python
    if spell.channeled:
        seconds = max(seconds, spell.duration)
```
add:
```python
    grace = sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                for e in t.effects if e.kind == "crit_haste_pct")
    if grace and not spell.channeled:
        # a crit speeds up the next cast (Nature's Grace, #397): on average by the crit chance
        seconds *= 1 - grace / 100 * min(1.0, (stats.crit_pct + mods.crit_chance_bonus) / 100)
```

## Step 2: `src/wowforever/classes/druid.py`
Add to `TALENT_EFFECTS`:
```python
    "Nature's Grace": (
        EffectRule("crit_haste_pct", r"reducing your global cooldown by (\d+(?:\.\d+)?)%", ("all",)),
    ),
```
and delete the `UNMODELED` line `    "Nature's Grace": "proc: spell crits speed up the next cast",`.

Nothing else changes.

## Done when
- `tests/test_natures_grace.py` passes; no other new failures apart from druid pins.
