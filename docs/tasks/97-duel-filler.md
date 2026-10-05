# Task #97: duels pick their own filler; Frost Nova into Shatter against melee

Make `tests/test_duel_filler.py` pass without breaking the rest of the suite. Edit `src/wowforever/scenarios.py`, `src/wowforever/classes/mage_rotation.py`, `src/wowforever/pvp/duel.py`, `src/wowforever/focus.py` and `src/wowforever/report.py`. Do not edit the tests.

## Why
Duels and the battleground reuse the filler that's best for questing kills/hour, which includes drinking. A mage in a duel casts whatever wins the fight. And Frost Nova into a Shatter crit (or a frozen Ice Lance) is the classic melee combo, which isn't modeled.

## 1. `scenarios.py`: `usable_fillers(char, names, target_level, assumptions) -> list[SpellRank]`
The best learned rank of each name, keeping only spells with modeled damage (`_cast(...)[0] > 0`), in `names` order. Rewrite `_best_result` to use it (behaviour unchanged).

## 2. `mage_rotation.py`: `frozen_hit_gain(char, filler, *, target_level, assumptions) -> float`
The extra damage of one hit on a frozen target, over spending that time on the filler:
- If Ice Lance is taken and learned: `ev(Ice Lance at 4x damage and 4x coefficient, frozen mods) - filler_dps * GCD_SECONDS`.
- Otherwise: `ev(filler, frozen mods) - ev(filler, normal mods)`. Without Shatter this is 0.

`filler_dps` is the filler's own `ev / cast` with talent mods, without weaves or freezes. Frozen mods are `modifiers_for(spell, cls, ranks, {"frozen"})`, so Shatter's crit applies. Use the same `ev` as `rotation` (sub-20 penalty, level scaling, non-sustained).

## 3. `duel.py`
- `MageSide` gains `nova_dps: float = 0.0`, the extra DPS against melee. It's a new last field with a default, so existing constructors still work.
- `mage_side(char, filler)` sets `nova_dps = frozen_hit_gain(...) / nova_cooldown` when Frost Nova is learned. `nova_cooldown` = Frost Nova's cooldown + the Improved Frost Nova `cooldown` effect (negative), as in `calc/pvp_axes.py`. One frozen hit per Nova: the first hit breaks the root.
- `duel()` uses `mage.dps + mage.nova_dps` against kits with `role == "melee"`, and `mage.dps` otherwise.
- New `best_scenario_scores(char, fillers, kits) -> dict`: for each scenario in `scenario_scores`, the result of the filler with the highest score for that scenario, ties going to the earlier filler. Each entry gains `"spell": filler.name`.

## 4. Callers
- `focus.pvp_score_fn` and `report.score_build` use `best_scenario_scores(char, usable_fillers(char, default_params("questing", level).fillers, level, assumptions), kits)` for the duel scenarios. Report rows gain `"spell"`.
- The battleground uses the filler with the best battleground score from the same list, and its report row gains `"spell"`.
- Survival and control axes keep the questing filler.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_duel_filler.py` fails with `ImportError` on `usable_fillers` / `frozen_hit_gain` / `best_scenario_scores`. That's the expected failure; implementing them is the task. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Start with `scenarios.py`, then `mage_rotation.py`, then `duel.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_duel_filler.py tests/test_duel.py tests/test_rotation.py`, then run the full suite once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
