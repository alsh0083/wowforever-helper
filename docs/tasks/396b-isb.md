# Task #396 (part 2): Improved Shadow Bolt

Make `tests/test_improved_shadow_bolt.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/caster.py` first, then `src/wowforever/classes/warlock.py`. Run the test
  file, then the fast suite once. Warlock regression pins (`tests/test_kit_stats.py`, opponent kits,
  `tests/test_dungeon_mana.py`) may move; Claude re-derives them.
- Before you start, every test in `tests/test_improved_shadow_bolt.py` fails with an ImportError.

## Why
Improved Shadow Bolt: a Shadow Bolt crit makes the target take 20% more Shadow damage for 12 s. Best effort
(owner OK 2026-10-16): its uptime is the chance that one of the Shadow Bolts cast in the last 12 s critted, and it
raises all the rotation's Shadow damage by 20% x uptime. Two new effect kinds carry it: `crit_debuff_pct` and
`crit_debuff_seconds`, each with `applies_to = (trigger spell, school it raises)`. The filler choice doesn't
account for the debuff.

## Step 1: `src/wowforever/caster.py`
1. Add this function directly before `def consumed_period(`:
```python
def crit_debuff_uptime(crit: float, casts_per_second: float, seconds: float) -> float:
    """Share of the time a debuff applied by a crit (Improved Shadow Bolt, #396) is up: the chance that one of the
    casts in the last `seconds` critted."""
    return 1 - (1 - crit) ** (casts_per_second * seconds) if casts_per_second > 0 else 0.0
```
2. In `caster_rotation`, the line `    time_left, dps, mana, used = 1.0, 0.0, 0.0, []` becomes
```python
    time_left, dps, mana, used = 1.0, 0.0, 0.0, []
    by_school: list[tuple[tuple[str, ...], float]] = []   # (schools, damage per second) of each cast spell
```
3. In the `for kind in ("dots", "cooldowns"):` loop, directly after the line `            dps += ev / period` add
   `            by_school.append((spell.schools, ev / period))`.
4. Replace the block at the end of the function:
```python
    if best is not None:
        dps += time_left * best[0] / best[1]
        mana += time_left * best[2] / best[1]
        used.append(best[3])
    return CasterRotation(dps=dps, mana_per_second=mana - regen, regen_per_second=regen, spells=tuple(used))
```
   with:
```python
    if best is not None:
        dps += time_left * best[0] / best[1]
        mana += time_left * best[2] / best[1]
        used.append(best[3])
        by_school.append((learned(best[3]).schools, time_left * best[0] / best[1]))
        # a debuff that a crit of the filler puts on the target (Improved Shadow Bolt, #396)
        for talent in cls.talents:
            rank = ranks.get(talent.talent_id, 0)
            pct = {e.applies_to: e.values[rank - 1] for e in (talent.effects if rank > 0 else ())
                   if e.kind == "crit_debuff_pct"}
            secs = {e.applies_to: e.values[rank - 1] for e in (talent.effects if rank > 0 else ())
                    if e.kind == "crit_debuff_seconds"}
            for (trigger, school), bonus in pct.items():
                if trigger != best[3] or (trigger, school) not in secs:
                    continue
                spell = learned(trigger)
                crit = min(1.0, (stats.crit_pct + modifiers_for(spell, cls, ranks).crit_chance_bonus) / 100)
                uptime = crit_debuff_uptime(crit, time_left / best[1], secs[(trigger, school)])
                dps += bonus / 100 * uptime * sum(d for schools, d in by_school if school in schools)
    return CasterRotation(dps=dps, mana_per_second=mana - regen, regen_per_second=regen, spells=tuple(used))
```

## Step 2: `src/wowforever/classes/warlock.py`
Add to `TALENT_EFFECTS`:
```python
    "Improved Shadow Bolt": (
        EffectRule("crit_debuff_pct", r"Shadow damage taken by the target from your attacks by (\d+(?:\.\d+)?)%",
                   ("Shadow Bolt", "shadow")),
        EffectRule("crit_debuff_seconds", r"from your attacks by \d+(?:\.\d+)?% for (\d+(?:\.\d+)?) sec",
                   ("Shadow Bolt", "shadow")),
    ),
```
and delete the `UNMODELED` line `    "Improved Shadow Bolt": "damage: Shadow Bolt crits raise Shadow damage taken",`.

Nothing else changes.

## Done when
- `tests/test_improved_shadow_bolt.py` passes (4 tests); no other new failures apart from warlock pins.
