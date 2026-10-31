# 444: pushback rules match the 70685 wording

**Goal:** the four `pushback_pct` effect rules read both the 70425 and the 70685 rank text (#444).

**Interface:** no new names. Edit only the regex string inside four existing `EffectRule("pushback_pct", ...)` calls.

**Inputs:** `data/datasets/1.60.1.70685.json` (the test loads it; you don't need to open it).

**Constraints:** touch only these four files: `src/wowforever/classes/druid.py`, `priest.py`, `shaman.py`,
`warlock.py`. Keep the kind, the `applies_to` tuple and everything else in each call as it is. One capture group,
the percentage, as now: `(\d+(?:\.\d+)?)`. Lines under 120 characters (split the string with implicit
concatenation inside the parentheses if needed).

**Done when:** `.venv/Scripts/python -m pytest -q tests/test_70685_pushback.py tests/test_side_immunity_pushback.py`
passes (the second file checks the old text still parses).

## Rank text (last rank of each; lower ranks differ only in the number)

| File | Talent | 70425 text (must still match) | 70685 text (must match too) |
|---|---|---|---|
| druid.py | Nature's Focus | Gives you a 70% chance to avoid interruption caused by damage while casting Arcane and Nature spells. | Gives your Arcane and Nature spells a 70% chance to not lose casting time when you take damage. |
| priest.py | Twilight Focus | Gives you a 70% chance to avoid interruption caused by damage while casting any spell. | Gives your spells a 70% chance to not lose casting time when you take damage. |
| shaman.py | Eye of the Storm | Reduces the pushback suffered from damaging attacks while casting Lightning Bolt, Chain Lightning, and Lava Burst by 70%. | Gives your Lightning Bolt, Chain Lightning, and Lava Burst spells a 70% chance to not lose casting time when you take damage. |
| warlock.py | Intensity | Gives you a 70% chance to resist interruption caused by damage while casting or channeling any Destruction spell. | Gives your Destruction spells a 70% chance to not lose casting time when you take damage. |

`mage.py` already reads the new wording for Burning Soul with
`r"(\d+(?:\.\d+)?)% chance to not lose casting time"`; use the same idea. A simple way that keeps one capture
group: `r"(\d+(?:\.\d+)?)% chance to (?:avoid interruption|not lose casting time)"` (druid, priest);
`resist interruption` for warlock. For Eye of the Storm the number sits at the end of the old text and before
"chance" in the new, so use a lookahead or two alternatives with one group, e.g.
`r"(?:Lava Burst by |Lava Burst spells a )(\d+(?:\.\d+)?)%"`.

## Steps, in this order
1. `src/wowforever/classes/druid.py`: the `"Nature's Focus"` entry.
2. `src/wowforever/classes/priest.py`: the `"Twilight Focus"` entry.
3. `src/wowforever/classes/shaman.py`: the `"Eye of the Storm"` entry.
4. `src/wowforever/classes/warlock.py`: the `"Intensity"` entry.
5. Then run the Done-when command once.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Before the change, the 4 tests in `tests/test_70685_pushback.py` fail; nothing else should.
- Make the edits before running any tests. Don't re-check things this spec states, and don't create files.
