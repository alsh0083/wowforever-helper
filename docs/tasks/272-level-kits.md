# Task #272: opponent kits at the duel's level

Make `tests/test_level_kits.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/pvp/kit_stats.py` and `src/wowforever/pvp/duel.py`.

## Why
`load_kits()` reads only each kit's `[at_60]` values, so PvP scores at levels 20-50 duel level-60 opponents. Kits need level-L health, DPS and opener damage, scaled from the config values by the damage engine's level-L / level-60 ratio for the kit's community build.

## Change
1. **`src/wowforever/pvp/kit_stats.py`:**
   - Add `import functools` and:
     ```python
     def kit_ranks_at(build, cls, level: int) -> dict[int, int]:
         """The build's talent ranks at `level`: its first level - 9 points (the first comes at 10), in the
         build's order, or, without one, its final talents filled lowest tree row first (then talent id)."""
         points = max(0, level - 9)
         order = build.order_ids(cls)
         if order is None:
             final = build.final_ids(cls)
             row = {t.talent_id: t.row for t in cls.talents}
             order = [tid for tid in sorted(final, key=lambda t: (row[t], t)) for _ in range(final[tid])]
         ranks: dict[int, int] = {}
         for tid in order[:points]:
             ranks[tid] = ranks.get(tid, 0) + 1
         return ranks
     ```
   - Add `engine_at(kit_id: str, level: int) -> tuple[float, float]`, decorated `@functools.lru_cache(maxsize=None)`: the same body as `engine_at_60`, but with `stats = stat_table(class_name).at(level)` and `ranks = kit_ranks_at(build, cls, level)`. Docstring: "(health, sustained DPS vs cloth) for one kit at `level`, from the damage engine (#272)." Leave `engine_at_60` unchanged.
2. **`src/wowforever/pvp/duel.py`:**
   - `Kit` gets a last field: `at_level: int = 60  # level its health/DPS describe; 60 = config values (#272)`.
   - Rename the current body of `load_kits` into `_config_kits(directory: Path) -> list[Kit]` (same code, unchanged).
   - Add, with `import functools` and `import dataclasses` at the top:
     ```python
     @functools.lru_cache(maxsize=None)
     def _kits_at(directory: Path, level: int) -> tuple[Kit, ...]:
         kits = _config_kits(directory)
         if level == 60:
             return tuple(kits)
         from wowforever.pvp.kit_stats import KIT_BUILDS, engine_at   # lazy: kit_stats runs the engines
         out = []
         for kit in kits:
             if kit.id not in KIT_BUILDS:
                 out.append(kit)            # no engine build (the mage kit): level-60 values, at_level stays 60
                 continue
             h, d = engine_at(kit.id, level)
             h60, d60 = engine_at(kit.id, 60)
             out.append(dataclasses.replace(kit, health=kit.health * h / h60, dps=kit.dps * d / d60,
                                            opener_damage=kit.opener_damage * d / d60, at_level=level))
         return tuple(out)


     def load_kits(directory: Path = OPPONENTS, level: int = 60) -> list[Kit]:
         """Every opponent kit in `directory`, sorted by id, at `level` (#272): config values at 60,
         engine kits scaled by their level / 60 engine ratio below it."""
         return list(_kits_at(directory, level))
     ```
     (`dataclasses` may already be imported as `from dataclasses import dataclass`; add `import dataclasses` anyway, or use `replace` from it.)
Change nothing else: callers keep calling `load_kits()`, and the report wiring is a separate step.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_level_kits.py` fails with `ImportError: cannot import name 'engine_at'`. That's the expected failure. The engine tests take a few seconds each. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md): `kit_stats.py` first, then `duel.py`.

## Done when
`.venv/Scripts/python -m pytest tests/test_level_kits.py tests/test_duel.py tests/test_class_pvp.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`.
