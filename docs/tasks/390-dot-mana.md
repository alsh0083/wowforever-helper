# Task #390: drop a DoT or cooldown when the mana budget is better spent on the filler

Make `tests/test_dot_mana.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/melee_scenarios.py` first, then `src/wowforever/caster.py`, then
  `src/wowforever/classes/engines.py`. Run the test file after each, then the fast suite once. Caster
  regression pins (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, opponent kits) may move; Claude
  re-derives them.
- Before you start, every test in `tests/test_dot_mana.py` fails.

## Why
`caster_rotation` keeps every DoT up whenever its damage is positive. In a mana-limited fight that mana can be
worth more on the filler: the Smite priest scores 161.88 in the dungeon with Devouring Plague and 176.88
without it. The rotation doesn't know the fight's mana budget, so the caster offers variants and the scenario
picks.

## Step 1: `src/wowforever/melee_scenarios.py`
1. In `class Output`, after the `mana_cooldown` field (and its two comment lines), add:
   ```python
       alternatives: tuple[Output, ...] = ()   # the same rotation with one DoT or cooldown dropped (#390);
                                               # the dungeon and raid scores take the best
   ```
2. Rename the existing `def raid_dps(out: Output, mana: float, p) -> float:` to
   `def _raid_dps_one(out: Output, mana: float, p) -> float:` (body unchanged), and add above it:
   ```python
   def raid_dps(out: Output, mana: float, p) -> float:
       """The best of `out` and its alternatives (#390) on the mana budget; see _raid_dps_one."""
       return max(_raid_dps_one(o, mana, p) for o in (out, *out.alternatives))
   ```
   Move the old docstring's text with the body: `_raid_dps_one` keeps it.

## Step 2: `src/wowforever/caster.py`
1. `caster_rotation` gains a keyword argument `skip: Collection[str] = ()` after `drink_mana_per_second`
   (import `Collection` from `collections.abc` next to `Mapping, Sequence`).
2. In the `for name in plan.get(kind, ()):` loop, the first line of the body becomes
   ```python
               if name in skip:
                   continue
               spell = learned(name)
   ```
   Add one sentence to the docstring: "`skip` names DoTs and cooldowns to leave out (#390)."

## Step 3: `src/wowforever/classes/engines.py`, `caster_output`
Replace the body after the imports with:
```python
    def one(skip=()):
        r = caster_rotation(class_name, stats, spells, cls, ranks, target,
                            drink_mana_per_second=drink_mana_per_second, skip=skip)
        gross = r.mana_per_second + r.regen_per_second
        fallback = r.dps * min(1.0, r.regen_per_second / gross) if gross > 0 else r.dps
        if "life_tap" in cfg:
            fallback = life_tap_fallback(r.dps, r.mana_per_second, stats.level, cfg["life_tap"])
        return r, Output(r.dps, r.mana_per_second, fallback, ranged=True)

    cfg = caster_config(class_name)
    r, out = one()
    filler = r.spells[-1] if r.spells and r.spells[-1] in class_module(class_name).ROTATION["fillers"] else None
    alternatives = tuple(one((name,))[1] for name in r.spells if name != filler)
    return replace(out, alternatives=alternatives)
```
and add the imports `from dataclasses import replace` and `from wowforever.classes import class_module`
inside the function next to the others. Update the docstring: "...; once dry, a caster keeps casting at the
rate its regen pays for. It also offers the rotation with each DoT or cooldown dropped (#390)."

Nothing else changes.

## Done when
- `tests/test_dot_mana.py` passes (4 tests); no other new failures apart from caster pins.
