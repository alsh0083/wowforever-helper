# 443b: Ice Barrier's Frost damage (1.60.1.70685)

**Goal:** Ice Barrier's new Frost damage bonus counts in mage scoring, with the "while shielded" half behind an
assumption toggle (#443).

**Interface:** no new functions. Edits in three files (below). The test imports only existing names.

**Done when:** `.venv/Scripts/python -m pytest -q tests/test_70685_ice_barrier.py` passes (3 tests). This branch
pins 1.60.1.70685; other fast-suite failures here belong to other tasks.

## The rank text (70685, 1 rank)
"Shield yourself, absorbing 447 damage and increasing your Frost damage by 3% for 1 min. While shielded, your
Frost damage is increased by an additional 3% and you do not lose casting time when you take damage."

## Steps, in this order
1. `src/wowforever/classes/mage.py`
   - In `UNMODELED`, delete the line `"Ice Barrier": "defensive: absorb shield",` (a talent may be in only one
     of `TALENT_EFFECTS` / `UNMODELED`).
   - In `TALENT_EFFECTS`, add an `"Ice Barrier"` entry right before `"Improved Frostbolt": (`, with two rules:
     - `EffectRule("damage_pct", r"increasing your Frost damage by (\d+(?:\.\d+)?)%", ("frost",))`
     - `EffectRule("damage_pct", r"Frost damage is increased by an additional (\d+(?:\.\d+)?)%",
       ("frost", "@shielded"))` (split over two lines to stay under 120 characters).
     A token starting with `@` makes a rule apply only when that condition is in the `conditions` set.
2. `src/wowforever/classes/mage_rotation.py`, function `rotation`: right after the line
   `conditions = frozenset({"sustained"}) if sustained else frozenset()`, add `"shielded"` to `conditions` when
   `assumptions["ice_barrier_shield_holds"]` is true (`conditions |= {"shielded"}`), with a short comment:
   Ice Barrier's extra Frost damage while the shield holds (#443).
3. `config/assumptions.toml`: append a table in the same format as the others:
   - `[ice_barrier_shield_holds]`, `value = true`, `options = [true, false]`
   - `why = "Ice Barrier (1.60.1.70685) adds 3% Frost damage for its minute and another 3% while the shield
     holds. On a boss nothing hits the mage, so the shield holds; in PvP it breaks fast."` (one line)
   - `source = "Ice Barrier rank text, 1.60.1.70685; issue #443 (best-effort)"`, `tested = ""`,
     `talents = ["Ice Barrier"]`
4. Then run the Done-when command once.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Before the change, the 3 tests in `tests/test_70685_ice_barrier.py` fail.
- Make the edits before running any tests. Don't re-check things this spec states, and don't create files.
