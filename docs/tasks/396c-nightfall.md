# Task #396 (part 3): Nightfall

Make `tests/test_nightfall.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/caster.py` first, then `src/wowforever/classes/warlock.py`. Run the test
  file, then the fast suite once. Warlock regression pins (`tests/test_kit_stats.py`, opponent kits,
  `tests/test_dungeon_mana.py`) may move; Claude re-derives them.
- Before you start, the tests in `tests/test_nightfall.py` fail.

## Why
Nightfall: Corruption, Drain Soul, Drain Life and Wrack have a 4% chance per damaging tick to make the next Shadow
Bolt instant. Best effort (owner OK 2026-10-16): only the rotation's kept-up DoTs' ticks count, each proc saves
Shadow Bolt's cast time minus the global cooldown, and that time goes to more Shadow Bolts. A new effect kind
`instant_proc_pct` carries it; `applies_to` lists the trigger spells and the made-instant spell as an `@` token.

## Step 1: `src/wowforever/caster.py`, `caster_rotation`
Directly before the line `        by_school.append((learned(best[3]).schools, time_left * best[0] / best[1]))`, add:
```python
        # procs that make the filler instant (Nightfall, #396): each saves its cast time minus the GCD, and the
        # saved time goes to more of the filler
        for talent in cls.talents:
            rank = ranks.get(talent.talent_id, 0)
            for e in (talent.effects if rank > 0 else ()):
                if e.kind != "instant_proc_pct" or f"@{best[3]}" not in e.applies_to:
                    continue
                ticks = sum(1 / s.tick_period for s in map(learned, used) if s is not None and s.tick_period > 0
                            and s.name in e.applies_to and s.name in plan.get("dots", ()))
                extra = ticks * e.values[rank - 1] / 100 * max(0.0, best[1] - GCD_SECONDS) / best[1]
                dps += extra * best[0]
                mana += extra * best[2]
```

## Step 2: `src/wowforever/classes/warlock.py`
Add to `TALENT_EFFECTS`:
```python
    "Nightfall": (
        EffectRule("instant_proc_pct", r"Wrack spells a (\d+(?:\.\d+)?)% chance to cause you to enter a Shadow Trance",
                   ("Corruption", "Drain Soul", "Drain Life", "Wrack", "@Shadow Bolt")),
    ),
```
and delete the `UNMODELED` line `    "Nightfall": "proc: Shadow Trance from drains and Corruption",`.

Nothing else changes.

## Done when
- `tests/test_nightfall.py` passes; no other new failures apart from warlock pins.
