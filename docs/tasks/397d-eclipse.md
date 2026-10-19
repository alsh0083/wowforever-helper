# Task #397 (part 3): Eclipse as a mixed Wrath + Starfire filler

Make `tests/test_eclipse.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/classes/druid.py`, then `src/wowforever/caster.py`, then
  `src/wowforever/classes/engines.py`. Run the test file, then the fast suite once. Druid regression pins
  (`tests/test_kit_stats.py`, opponent kits) may move; Claude re-derives them.
- Before you start, most tests in `tests/test_eclipse.py` fail.

## Why
Eclipse: each Wrath cuts the cast time of the next 2 Starfires by 0.5 s. The caster rotation picks one filler, so it
never weighs a Wrath-then-Starfire cycle. A class can now name a mixed filler in `ROTATION["filler_mix"]` =
(opener, follower, followers per opener, condition): the follower casts with that condition on, so a talent rule with
`@<condition>` applies to it. The mix competes with the single fillers.

## Step 1: `src/wowforever/classes/druid.py`
1. Add to `TALENT_EFFECTS`:
```python
    "Eclipse": (
        EffectRule("cast_time", r"cast time of your next 2 Starfire spells by (\d+(?:\.\d+)?) sec",
                   ("Starfire", "@eclipse"), sign=-1),
    ),
```
   and delete the `UNMODELED` line `    "Eclipse": "proc: Wrath speeds up Starfire",`.
2. In `ROTATION`, after the `"fillers"` line add
```python
    # one Wrath, then two Starfires with Eclipse's cut (#397)
    "filler_mix": ("Wrath", "Starfire", 2, "eclipse"),
```

## Step 2: `src/wowforever/caster.py`, `caster_rotation`
1. Directly after the filler loop (after the line `            best = (ev, seconds, cost, name)` and before
   `    if best is not None:`), add:
```python
    mix_schools: tuple[str, ...] = ()
    mix = plan.get("filler_mix")
    if mix is not None:
        # a mixed filler: an opener, then followers cast with its condition on (Eclipse, #397)
        first, follow, count, condition = mix
        a, b = learned(first), learned(follow)
        if a is not None and b is not None:
            ev1, s1, c1 = cast(a, stats, cls, ranks, target_level, assumptions, *boosts(first))
            conditions, extra = boosts(follow)
            ev2, s2, c2 = cast(b, stats, cls, ranks, target_level, assumptions, conditions | {condition}, extra)
            mixed = (ev1 + count * ev2, s1 + count * s2, c1 + count * c2, f"{first} + {follow}")
            if mixed[0] > 0 and (best is None or worth(*mixed[:3]) > worth(*best[:3])):
                best = mixed
                mix_schools = tuple(dict.fromkeys(a.schools + b.schools))
```
2. The line `        by_school.append((learned(best[3]).schools, time_left * best[0] / best[1]))` becomes
```python
        filler = learned(best[3])
        by_school.append((filler.schools if filler is not None else mix_schools, time_left * best[0] / best[1]))
```
3. In the crit-debuff block a few lines below, the line `                spell = learned(trigger)` stays; nothing else
   changes there.

## Step 3: `src/wowforever/classes/engines.py`, `caster_facts`
The line `            "filler": next((s for s in r.spells if s in plan.get("fillers", ())), None)}` becomes
```python
            "filler": next((s for s in r.spells if s in plan.get("fillers", ()) or " + " in s), None)}
```

Also in `caster_output`, the line
`    filler = r.spells[-1] if r.spells and r.spells[-1] in class_module(class_name).ROTATION["fillers"] else None`
becomes
```python
    fillers = class_module(class_name).ROTATION["fillers"]
    filler = r.spells[-1] if r.spells and (r.spells[-1] in fillers or " + " in r.spells[-1]) else None
```

Nothing else changes.

## Done when
- `tests/test_eclipse.py` passes; no other new failures apart from druid pins.
