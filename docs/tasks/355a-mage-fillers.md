# Task #355, part A: Frost Blast and Arcane Wrath as mage fillers

Make `tests/test_70425_mage_fillers.py` and `tests/test_scenarios.py` pass without breaking the rest of the fast
suite (`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing; the package and dataset are ready.
- Before you start, `tests/test_70425_mage_fillers.py` fails and so does `test_scenarios.py`'s filler test.
  Other failures in the fast suite belong to other tasks. After your change the mage pins in
  `tests/test_dungeon_mana.py` may move; Claude re-derives them. Any other new failure is not expected.
- Edit only `config/scenarios.toml` and `src/wowforever/scenarios.py`. Don't re-check things this spec states.

## Why
Build 1.60.1.70425 adds two mage spells:
- **Frost Blast**, a baseline spell: 1.5 s cast with a 40% slow.
- **Arcane Wrath**, taught by a new 1-point Arcane talent. The talent's rank text ends: "This spell gains
  additional Spell Damage equal to 5% of your maximum Mana."

The mage picks its filler from `[questing] fillers` in `config/scenarios.toml`. A spell a talent teaches
(Arcane Wrath, Pyroblast, Ice Lance...) is in the class's spell list whether or not the build takes the
talent, so the model must drop it from a `Character` whose build doesn't take that talent. The mana bonus is
spell damage, so it adds `coefficient × 5% × max mana` to the spell's base damage (expected damage adds
`coefficient × spell power` to the base).

## Steps

### 1. `config/scenarios.toml`
Append `"Frost Blast", "Arcane Wrath"` to the `fillers` list (keep the four existing names first, in order).

### 2. `src/wowforever/scenarios.py`
- Add `import re` to the imports.
- Below the `Character` class, add a module-level cache `_TAUGHT: dict[int, dict[str, float]] = {}`, a compiled
  pattern for "gains additional Spell Damage equal to (N)% of your maximum Mana", and a function
  `_taught(cls: ClassData) -> dict[str, float]`. It maps each talent whose name is also the name of one of
  `cls.spells` (and has rank text) to that pattern's N in its last rank text, or 0.0 when the text doesn't
  match. Cache the result per `id(cls)`.
- `Character` (a frozen dataclass): add a `__post_init__`. It builds a new spell tuple and stores it with
  `object.__setattr__(self, "spells", ...)`. For each spell in `self.spells`:
  - if its name is in `_taught(self.cls)` and the build doesn't take that talent (no talent of that name has
    `self.ranks.get(talent_id, 0) > 0`), leave it out;
  - if its name maps to a non-zero N, add `spell.coefficient * N / 100 * self.stats.mana` to both
    `min_damage` and `max_damage` (`dataclasses.replace`);
  - otherwise keep it as it is.

  Put a two-line comment at the top of `__post_init__` saying both rules (#355).

## Done when
- `tests/test_70425_mage_fillers.py` (4 tests) and `tests/test_scenarios.py` pass.
- No new failures in the fast suite apart from the mage dungeon pins.
