# Task #384 (part 2) / #396: longer DoTs and Improved Life Tap

Make `tests/test_dot_duration.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/caster.py` first, then `engines.py`, then the three class modules. Run the
  test file at the end, then the fast suite once. Priest, shaman and warlock regression pins
  (`tests/test_dungeon_mana.py`, `tests/test_dot_mana.py`'s dungeon values, `tests/test_kit_stats.py`, opponent
  kits) may move; Claude re-derives them.
- Before you start, every test in `tests/test_dot_duration.py` fails with an ImportError.

## Why
Improved Shadow Word: Pain (+6 s) and Call of Flame (+9 s Flame Shock) lengthen a DoT: more ticks at the same tick
damage. Improved Life Tap gives 20% more mana per tap. A new effect kind `dot_seconds` carries the extra seconds,
and `life_tap_pct` the Life Tap bonus.

## Step 1: `src/wowforever/caster.py`
1. Add these two functions directly before `def consumed_period(`:
```python
def longer_dot(spell: SpellRank, cls: ClassData, ranks: Mapping[int, int]) -> SpellRank:
    """`spell` with its talents' extra DoT seconds (Improved Shadow Word: Pain, Call of Flame, #384): more ticks, so
    its periodic damage and coefficient grow with the duration."""
    extra = sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                for e in t.effects if e.kind == "dot_seconds" and spell.name in e.applies_to)
    if extra <= 0 or spell.duration <= 0:
        return spell
    scale = (spell.duration + extra) / spell.duration
    return replace(spell, duration=spell.duration + extra, periodic_damage=spell.periodic_damage * scale,
                   periodic_coefficient=spell.periodic_coefficient * scale)


def life_tap_pct(cls: ClassData, ranks: Mapping[int, int]) -> float:
    """Percent more mana per Life Tap from the build's talents (Improved Life Tap, #396)."""
    return sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
               for e in t.effects if e.kind == "life_tap_pct")
```
2. In `caster_rotation`'s `for kind in ("dots", "cooldowns"):` loop, directly after
```python
            spell = learned(name)
            if spell is None:
                continue
```
   add
```python
            if kind == "dots":
                spell = longer_dot(spell, cls, ranks)
```
3. The line
   `    regen += caster_config(class_name).get("extra_regen_per_second", 0.0)   # Life Tap`
   becomes
```python
    regen += (caster_config(class_name).get("extra_regen_per_second", 0.0)        # Life Tap
              * (1 + life_tap_pct(cls, ranks) / 100))
```

## Step 2: `src/wowforever/classes/engines.py`
1. `life_tap_fallback`'s signature becomes
   `def life_tap_fallback(dps: float, drain: float, level: int, tap, bonus_pct: float = 0.0) -> float:`,
   its docstring gains the sentence ` Improved Life Tap adds `bonus_pct`% (#396).` before the closing `"""`, and
   its last line becomes
   `    return dps / (1 + drain * tap["gcd"] / ((rank[1] + level - rank[0]) * (1 + bonus_pct / 100)))`
2. In `caster_output`, add `from wowforever.caster import life_tap_pct` next to the `caster_rotation` import, and the
   line `            fallback = life_tap_fallback(r.dps, r.mana_per_second, stats.level, cfg["life_tap"])` becomes
```python
            fallback = life_tap_fallback(r.dps, r.mana_per_second, stats.level, cfg["life_tap"],
                                         bonus_pct=life_tap_pct(cls, ranks))
```

## Step 3: rules
1. `src/wowforever/classes/priest.py`: add to `TALENT_EFFECTS`
```python
    "Improved Shadow Word: Pain": (
        EffectRule("dot_seconds", r"Shadow Word: Pain spell by (\d+(?:\.\d+)?) sec", ("Shadow Word: Pain",)),
    ),
```
   and delete the `UNMODELED` line `    "Improved Shadow Word: Pain": "damage: longer Shadow Word: Pain",`.
2. `src/wowforever/classes/shaman.py`: in the existing `"Call of Flame": (` entry, add a second rule after the
   `damage_pct` one:
```python
        EffectRule("dot_seconds", r"duration of your Flame Shock spell by (\d+(?:\.\d+)?) sec", ("Flame Shock",)),
```
3. `src/wowforever/classes/warlock.py`: add to `TALENT_EFFECTS`
```python
    "Improved Life Tap": (
        EffectRule("life_tap_pct", r"Mana awarded by your Life Tap spell by (\d+(?:\.\d+)?)%", ("all",)),
    ),
```
   and delete the `UNMODELED` line `    "Improved Life Tap": "resource: +20% Life Tap mana",`.

Nothing else changes.

## Done when
- `tests/test_dot_duration.py` passes (8 tests); no other new failures apart from priest, shaman and warlock pins.
