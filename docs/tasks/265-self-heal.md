# Task #265 step 2: self-healing in the duel model

Make `tests/test_self_heal.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `config/pvp_self.toml`, `src/wowforever/pvp/duel.py` and `src/wowforever/pvp/class_pvp.py`. The test docstring has the hand-worked numbers.

## Why
Restoration and hybrid druids win duels by healing themselves; the duel model has no healing, so it understates them. A side may now spend a mana-limited healing budget, and does so only when that raises its score.

## Change
1. **`config/pvp_self.toml`, `[druid]` table:** add
   ```toml
   # self-healing in duels (#265): direct heals only (HoTs can't be stacked by recasting; later); share of mana spent healing (estimate)
   heals = ["Healing Touch", "Regrowth"]
   heal_mana_share = 0.5
   ```
2. **`src/wowforever/pvp/duel.py`:**
   - `MageSide` gets two last fields: `heal_hps: float = 0.0  # healing per second while casting heals (#265)` and `heal_budget: float = 0.0  # mana-limited healing for the fight`.
   - In `duel()`, replace the `t_mage = min(...)`, `t_opponent = min(...)` and `score = ...` lines with:
     ```python
     t_mage = min(max(t_mage, 0.0), max_fight)
     t_opponent = min(max(t_opponent, 0.0), max_fight)
     score = 0.5 if t_mage + t_opponent == 0 else t_opponent / (t_mage + t_opponent)
     if mage.heal_budget > 0 and mage.heal_hps > 0 and net > 0:
         # healing adds effective health but pauses damage (#265); heal only if the score rises
         h_mage = min(t_mage + mage.heal_budget / mage.heal_hps, max_fight)
         h_opp = min((mage.health - opening + mage.heal_budget) / net, max_fight)
         h_score = h_opp / (h_mage + h_opp)
         if h_score > score:
             t_mage, t_opponent, score = h_mage, h_opp, h_score
     ```
3. **`src/wowforever/pvp/class_pvp.py`:**
   - Add (import `GCD_SECONDS` from `wowforever.calc.ev`):
     ```python
     def heal_capacity(class_name: str, stats, spells: Sequence[SpellRank], cls: ClassData,
                       ranks: Mapping[int, int]) -> tuple[float, float]:
         """(healing per second while healing, mana-limited healing budget) from the class's direct heals (#265).

         Each heal in config `heals` (best rank learned at the stats' level) heals its average direct amount plus
         heal coefficient x the build's spell power per cast of max(GCD, cast time) seconds; the best per second
         is used, and the budget is mana x heal_mana_share x its healing per mana. Classes without `heals`: (0, 0)."""
     ```
     Body: `cfg = load_toml(CONFIG)[class_name]`, and return `(0.0, 0.0)` if `"heals"` isn't in it. `row = build_stats(class_name, stats, cls, ranks)`, `sp = getattr(row, "spell_power", 0.0)`. For each name, `spell = best_rank(spells, name, stats.level)`; skip it if None, or `spell.mana_cost <= 0`, or `spell.heal_max <= 0`. Then `amount = (spell.heal_min + spell.heal_max) / 2 + spell.heal_coefficient * sp`, `seconds = max(GCD_SECONDS, spell.cast_time)`. Keep the spell with the highest `amount / seconds`. Return `(amount / seconds, row.mana * cfg["heal_mana_share"] * amount / spell.mana_cost)` for it, or `(0.0, 0.0)` if none qualified.
   - In `class_side`, compute `heal_hps, heal_budget = heal_capacity(class_name, stats, spells, cls, ranks)` and pass both to `MageSide(...)`.
   - Add one line to the module docstring: Druids heal themselves with direct heals when that helps (#265).

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_self_heal.py` fails with `ImportError: cannot import name 'heal_capacity'`. That's the expected failure. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above.

## Done when
`.venv/Scripts/python -m pytest tests/test_self_heal.py tests/test_duel.py tests/test_class_pvp.py tests/test_thorns_pvp.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`.
