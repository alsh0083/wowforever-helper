# Task #268: hunter traps become one rank with their effect's damage

Make `tests/test_trap_ranks.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/normalize_spells.py`. The test docstring has the rule.

## Why
Each hunter trap trains as two spells at each level: the trap you place (only Effect 104, with the mana cost) and the effect that deals its damage. The effect is named like the trap (Immolation Trap) or "<trap> Effect" (Explosive Trap Effect). Today both become ranks, so Immolation Trap folds into 10 ranks, and the placed trap carries no damage. AoE pulls for hunters (#262) need the trap's damage on the trap.

## Change (all in `src/wowforever/normalize_spells.py`, in this order)
1. Change `from dataclasses import dataclass` to `from dataclasses import dataclass, replace`.
2. After the line `EFFECT_AREA_TRIGGER = 179    # triggers an area effect` add
   ```python
   EFFECT_TRAP = 104            # summon a trap object (Immolation Trap, Explosive Trap)
   ```
3. In `class_spells`, after the line `    trainable = _damage_over_heal(trainable, indexes)` add
   ```python
       traps = _trap_effects(trainable, indexes)
       trap_hits = set(traps.values())
       trainable = [t for t in trainable if t[2] not in trap_hits]
   ```
4. In `class_spells`, replace
   ```python
           ranks.append(_build_rank(spell_id, name, rank_of_name[name], level, indexes, tick_damage,
                                    sibling_damage=sibling_damage))
       return tuple(ranks)
   ```
   with
   ```python
           rank = _build_rank(spell_id, name, rank_of_name[name], level, indexes, tick_damage,
                              sibling_damage=sibling_damage)
           if spell_id in traps:
               # the placed trap deals its effect spell's damage (#268)
               hit = _build_rank(traps[spell_id], name, rank.rank, level, indexes, tick_damage,
                                 sibling_damage=sibling_damage)
               rank = replace(rank, **{f: getattr(hit, f) for f in _TRAP_DAMAGE_FIELDS})
           ranks.append(rank)
       return tuple(ranks)
   ```
5. Just before `def ranks_of(`, add
   ```python
   _TRAP_DAMAGE_FIELDS = ("schools", "min_damage", "max_damage", "coefficient", "periodic_damage",
                          "periodic_coefficient", "tick_period", "duration", "damage_per_level", "scaling_max_level")


   def _trap_effects(trainable: list[tuple[str, int, int]], indexes: _Indexes) -> dict[int, int]:
       """Trap spell id -> the trainable spell that deals its damage (#268): a trap (only Effect 104) and its
       effect train at the same level, the effect named like the trap or "<trap> Effect"; lowest id wins."""
       by_key: dict[tuple[str, int], list[int]] = {}
       for name, level, spell_id in trainable:
           by_key.setdefault((name, level), []).append(spell_id)

       def is_trap(spell_id: int) -> bool:
           effects = indexes.effects.get(spell_id, [])
           return bool(effects) and all(e["Effect"] == str(EFFECT_TRAP) for e in effects)

       out: dict[int, int] = {}
       for name, level, spell_id in trainable:
           if not is_trap(spell_id):
               continue
           partners = [i for n in (name, f"{name} Effect") for i in by_key.get((n, level), [])
                       if i != spell_id and not is_trap(i)]
           if partners:
               out[spell_id] = min(partners)
       return out


   ```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, 2 of the 4 tests in `tests/test_trap_ranks.py` fail with `AssertionError`. That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above, with hunks in file order. Leave the dataset files alone; Claude re-normalizes the data afterwards.

## Done when
`.venv/Scripts/python -m pytest tests/test_trap_ranks.py tests/test_spell_siblings.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`.
