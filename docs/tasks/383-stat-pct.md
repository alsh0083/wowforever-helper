# Task #383: percent-stat talents for shaman, druid and paladin

Make `tests/test_stat_pct_talents.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order; run the test file after step 3 and at the end, then the fast suite once.
  Shaman, druid and paladin regression pins (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, opponent
  kits, `tests/test_class_engine.py`) may move; Claude re-derives them.
- Before you start, every test in `tests/test_stat_pct_talents.py` fails with an ImportError.

## Why
These talents read "Increases your <stat> by N%", the shape of Mental Strength (#356), but have no rule. Casters
apply `stat_pct` rules in `caster.talent_stats`; melee rows (paladin Retribution, Feral, Enhancement) apply none.

## Step 1: `src/wowforever/caster.py`, `talent_stats`
The lines
```python
            stat = effect.applies_to[0]
            bumped = apply(class_name, stats, stat, getattr(stats, stat) * effect.values[rank - 1] / 100)
```
become
```python
            stat = effect.applies_to[0]
            if getattr(stats, stat, None) is None:       # Cat Form Strength on a caster row (#383)
                continue
            bumped = apply(class_name, stats, stat, getattr(stats, stat) * effect.values[rank - 1] / 100)
```

## Step 2: `src/wowforever/classes/engines.py`
1. Add this function directly before `def melee_build(`:
```python
def melee_talent_stats(class_name: str, stats: Any, cls: ClassData, ranks: Mapping[int, int]) -> Any:
    """The build's `stat_pct` talents (Divine Strength, Heart of the Wild, #383) on a melee row: a MeleeStats,
    or a hybrid's melee row."""
    from wowforever.melee_scenarios import HybridStats
    from wowforever.stat_weights import apply

    row = stats.melee if isinstance(stats, HybridStats) else stats
    for talent in cls.talents:
        rank = ranks.get(talent.talent_id, 0)
        if rank <= 0:
            continue
        for effect in talent.effects:
            if effect.kind != "stat_pct" or getattr(row, effect.applies_to[0], None) is None:
                continue
            stat = effect.applies_to[0]
            bumped = apply(class_name, stats, stat, getattr(row, stat) * effect.values[rank - 1] / 100,
                           melee_build=True)
            if bumped is not None:
                stats = bumped
    return stats
```
2. In `hybrid_output`, the line
   `            return melee_output(stats.melee, spells, cls, ranks, target, pack=pack)`
   becomes
```python
            stats = melee_talent_stats(class_name, stats, cls, ranks)
            return melee_output(stats.melee, spells, cls, ranks, target, pack=pack)
```

## Step 3: rules
1. `src/wowforever/classes/shaman.py`: add to `TALENT_EFFECTS` (anywhere inside the dict):
```python
    "Ancestral Knowledge": (
        EffectRule("stat_pct", r"Increases your Intellect by (\d+(?:\.\d+)?)%", ("intellect",)),
    ),
```
   and delete the `UNMODELED` line `    "Ancestral Knowledge": "buff: +10% Intellect",`.
2. `src/wowforever/classes/druid.py`: add to `TALENT_EFFECTS`:
```python
    "Heart of the Wild": (
        EffectRule("stat_pct", r"Increases your Intellect by (\d+(?:\.\d+)?)%", ("intellect",)),
        EffectRule("stat_pct", r"Cat Form your Strength is increased by (\d+(?:\.\d+)?)%", ("strength",)),
    ),
    "Living Spirit": (
        EffectRule("stat_pct", r"Increases your Spirit by (\d+(?:\.\d+)?)%", ("spirit",)),
    ),
```
   and delete the `UNMODELED` lines for `"Heart of the Wild"` and `"Living Spirit"`.
3. `src/wowforever/classes/paladin.py`: add to `TALENT_EFFECTS`:
```python
    "Divine Strength": (
        EffectRule("stat_pct", r"Increases your Strength by (\d+(?:\.\d+)?)%", ("strength",)),
    ),
    "Divine Intellect": (
        EffectRule("stat_pct", r"total Intellect by (\d+(?:\.\d+)?)%", ("intellect",)),
    ),
```
   and delete the `UNMODELED` lines for `"Divine Strength"` and `"Divine Intellect"`.

## Step 4: `src/wowforever/classes/paladin.py`, `output`
Add `    from wowforever.classes.engines import melee_talent_stats` after the two imports at the top of `output`,
and the line `    r = paladin_rotation(stats, spells, cls, ranks, target, pack=pack)` becomes
```python
    r = paladin_rotation(melee_talent_stats("paladin", stats, cls, ranks), spells, cls, ranks, target, pack=pack)
```

Nothing else changes.

## Done when
- `tests/test_stat_pct_talents.py` passes (9 tests); no other new failures apart from shaman, druid and paladin pins.
