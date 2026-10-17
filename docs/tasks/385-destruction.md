# Task #385: Destruction rotation: Shadowburn, Shadow and Flame's Fire bonus, Conflagrate consuming Immolate

Make `tests/test_destruction_rotation.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/caster.py` first, then `src/wowforever/classes/warlock.py`. Run the test
  file after each, then the fast suite once. Warlock regression pins (`tests/test_dungeon_mana.py`,
  `tests/test_kit_stats.py`, opponent kits) may move; Claude re-derives them.
- Before you start, every test in `tests/test_destruction_rotation.py` fails with an ImportError.

## Why
Shadowburn (a talent, 15 s cooldown) is never cast. Shadow and Flame also gives +10% Fire damage after Shadowburn
(a 20 s buff on a 15 s cooldown: always up), and its rank text says Conflagrate keeps Immolate 20% of the time per
rank; without it, Conflagrate consumes Immolate and Immolate only ticks until the next Conflagrate.

## Step 1: `src/wowforever/caster.py`
1. `from dataclasses import dataclass` becomes `from dataclasses import dataclass, replace`.
2. Add this function directly before `def caster_rotation(`:
```python
def consumed_period(duration: float, cooldown: float, keep_pct: float) -> float:
    """Seconds between casts of a DoT that a cooldown consumes (Conflagrate eats Immolate, #385): the DoT runs
    its full duration when kept (keep_pct%), else only until the next consuming cast."""
    keep = min(1.0, keep_pct / 100)
    return keep * duration + (1 - keep) * min(duration, cooldown)
```
3. In `caster_rotation`, replace this block:
```python
    for kind in ("dots", "cooldowns"):
        for name in plan.get(kind, ()):
            if name in skip:
                continue
            spell = learned(name)
            if spell is None:
                continue
            ev, seconds, cost = cast(spell, stats, cls, ranks, target_level, assumptions)
            cooldown = spell.cooldown + sum(
                e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                for e in t.effects if e.kind == "cooldown" and name in e.applies_to)
            period = spell.duration if kind == "dots" else max(cooldown, seconds)
```
with:
```python
    def cooldown_of(spell: SpellRank) -> float:
        return spell.cooldown + sum(
            e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
            for e in t.effects if e.kind == "cooldown" and spell.name in e.applies_to)

    consumers = {}   # DoT -> (seconds between the casts that consume it, % chance to keep it), #385
    for name, dot in plan.get("consumes", {}).items():
        spell = learned(name)
        if spell is None or name in skip:
            continue
        keep = sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                   for e in t.effects if e.kind == "proc_chance" and f"@keep_{dot}" in e.applies_to)
        consumers[dot] = (cooldown_of(spell), keep)

    for kind in ("dots", "cooldowns"):
        for name in plan.get(kind, ()):
            if name in skip:
                continue
            spell = learned(name)
            if spell is None:
                continue
            ev, seconds, cost = cast(spell, stats, cls, ranks, target_level, assumptions)
            cooldown = cooldown_of(spell)
            period = spell.duration if kind == "dots" else max(cooldown, seconds)
            if kind == "dots" and name in consumers and spell.duration > 0:
                # a consuming cooldown cuts the DoT short: only its ticks until then count (#385)
                direct, _, _ = cast(replace(spell, periodic_damage=0.0, periodic_coefficient=0.0), stats, cls,
                                    ranks, target_level, assumptions)
                period = consumed_period(spell.duration, *consumers[name])
                ev = direct + (ev - direct) * period / spell.duration
```
The lines after it (`if ev <= 0 or period <= 0 ...` and the rest of the loop) stay as they are.

## Step 2: `src/wowforever/classes/warlock.py`
1. In `ROTATION`, `"cooldowns": ("Conflagrate",),` becomes `"cooldowns": ("Conflagrate", "Shadowburn"),`, and add
   the line `    "consumes": {"Conflagrate": "Immolate"},` after the `"fillers"` line.
2. The `"Shadow and Flame"` entry in `TALENT_EFFECTS` becomes:
```python
    "Shadow and Flame": (
        EffectRule("damage_pct", r"Conflagrate increases all Shadow damage you deal by (\d+(?:\.\d+)?)%", ("shadow",)),
        EffectRule("damage_pct", r"Shadowburn increases all Fire damage you deal by (\d+(?:\.\d+)?)%", ("fire",)),
        EffectRule("proc_chance", r"Conflagrate has a (\d+(?:\.\d+)?)% chance not to consume Immolate",
                   ("@keep_Immolate",)),
    ),
```
3. In `CAVEAT`, `"Conflagrate on cooldown, "` becomes `"Conflagrate and Shadowburn on cooldown, "`.

Nothing else changes.

## Done when
- `tests/test_destruction_rotation.py` passes (5 tests); no other new failures apart from warlock pins.
