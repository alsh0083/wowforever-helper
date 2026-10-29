# 439: Missile Barrage reads the 70685 text

**Goal:** `missile_barrage_rule` reads both the 70425 and the 70685 Missile Barrage text (#439).

**Interface:** unchanged: `missile_barrage_rule(cls, rank: int) -> dict[str, float]` in
`src/wowforever/classes/mage_rotation.py`. Edit only the body of that function (lines ~72-81).

**Done when:**
`.venv/Scripts/python -m pytest -q tests/test_70685_missile_barrage.py tests/test_missile_barrage.py` passes.

## Rank texts (rank 2; rank 1 halves every number)

| Build | Text |
|---|---|
| 70425 (tests/test_missile_barrage.py) | Gives your Arcane Blast spell a 40% chance, your Arcane Missile hits a 10% chance, and your Arcane Wrath, Fireball, Frostbolt, and Frostfire Bolt spells a 20% chance to reduce ... |
| 70685 (tests/test_70685_missile_barrage.py) | Gives your Arcane Blast spell a 40% chance, and your Arcane Wrath, Fireball, Frostbolt, Frost Blast, and Frostfire Bolt spells a 20% chance to reduce ... |

## What the function returns
- `"Arcane Blast"`: the number in `Arcane Blast spell a N% chance`.
- `"Arcane Missiles"`: the number in `Arcane Missile hits a N% chance`, or `0.0` when the text has no such clause
  (70685). Keep the key either way: `rotation` reads `barrage["Arcane Missiles"]`.
- One key per spell named in `and your <names> spells a N% chance`, each with that N. Split `<names>` on
  `", and "`, `", "` and `" and "` (that order in one regex alternation: `r", and |, | and "`), so 70425 gives
  Arcane Wrath, Fireball, Frostbolt, Frostfire Bolt and 70685 also Frost Blast. A name regex that works:
  `r"and your ([A-Z][\w ,]*?) spells a (\d+(?:\.\d+)?)% chance"`.
- All values are floats. Update the docstring: per cast of each spell named, and per missile hit for
  "Arcane Missiles" when the text has that clause (0 on 70685, #439).

## Steps, in this order
1. Replace the body of `missile_barrage_rule` (keep the `import re` line and the `text = ...` line).
2. Then run the Done-when command once.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Before the change, the 2 tests in `tests/test_70685_missile_barrage.py` fail; nothing else.
- Make the edit before running any tests. Don't re-check things this spec states, and don't create files.
