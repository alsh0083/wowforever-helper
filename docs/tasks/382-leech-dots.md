# Task #382: leech DoTs (aura 53) carry periodic damage

Make `tests/test_leech_dots.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/normalize_spells.py`. **Make the edit first**, then run the test file,
  then the fast suite once. Don't regenerate any dataset; Claude does that.
- Before you start, `test_leech_and_plain_dots_read_the_same_periodic_damage[53]` fails and `[3]` passes.

## Why
Devouring Plague, Siphon Life and Drain Life apply aura 53 (periodic leech) instead of aura 3, so the DoT branch in
`_build_rank` never finds them and their periodic damage stays 0.

## Steps (`src/wowforever/normalize_spells.py`)
1. Below the line `AURA_DOT = 3 ...`, add
   `AURA_LEECH = 53               # periodic leech: damage over time that heals the caster (Devouring Plague, Siphon Life, Drain Life)`.
2. In `_build_rank`, the DoT lookup reads
   `if e["Effect"] == str(EFFECT_AURA) and e["EffectAura"] == str(AURA_DOT)), None)`.
   Change only the aura test to `e["EffectAura"] in (str(AURA_DOT), str(AURA_LEECH))`. Nothing else changes.

## Done when
- `tests/test_leech_dots.py` passes (2 tests), and the fast suite has no new failures.
