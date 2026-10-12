# Task #290: roots hold while the side heals

Make `tests/test_roots_while_healing.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/pvp/duel.py`. The test docstring has the hand-worked numbers.

## Why
Since #286, a root on the opponent being damaged breaks after threshold ÷ DPS. While the side heals, it attacks nobody, so its roots hold fully. The healing branches should use the time-weighted mean of the attacking damage rate and the healing damage rate.

## Change (all in `src/wowforever/pvp/duel.py`, in this order)
1. In `duel`, replace
   ```python
           # healing adds effective health but pauses damage (#265); heal only if the score rises
           h_mage = min(t_mage + mage.heal_budget / mage.heal_hps, max_fight)
           h_opp = min((mage.health - opening + mage.heal_budget) / net, max_fight)
   ```
   with
   ```python
           # healing adds effective health but pauses damage (#265); heal only if the score rises.
           # Roots hold fully while healing (#290): the fight's damage rate is the time-weighted mean.
           heal_time = mage.heal_budget / mage.heal_hps
           held = max(c["min_uptime"], 1 - _kiting_seconds(mage, kit, c) / 60)
           net_heal = kit.dps * physical * held * (1 - mage.immunity_share) - barrier
           mean_net = (net * t_mage + net_heal * heal_time) / (t_mage + heal_time)
           h_mage = min(t_mage + heal_time, max_fight)
           h_opp = min((mage.health - opening + mage.heal_budget) / mean_net, max_fight)
   ```
2. In `outnumbered`'s docstring, replace
   ```
       alone, as in a duel. Healing happens in phase 1 and counts only if the score rises. mage_uptime
       and opponent_uptime are phase 1's, the latter for `first`."""
   ```
   with
   ```
       alone, as in a duel. Healing happens in phase 1, with roots unbroken while it lasts (#290), and
       counts only if the score rises. mage_uptime and opponent_uptime are phase 1's, the latter for
       `first`."""
   ```
3. In `outnumbered`, after the line `    net1 = d_first + incoming(second, shared)[0] - barrier([first, second])` add
   ```python
       # while healing nobody is attacked, so the focus keeps a full root (#290)
       unbroken = dataclasses.replace(shared, root=side.root if side.root_targets >= 2 else 0.0)
       net1_heal = incoming(first, unbroken)[0] + incoming(second, shared)[0] - barrier([first, second])
   ```
4. Replace the `time_to_die` helper with
   ```python
       def time_to_die(health: float, phase1: float, rate1: float) -> float:
           if rate1 > 0 and rate1 * phase1 >= health:
               return health / rate1
           left = health - max(rate1, 0.0) * phase1
           return phase1 + left / net2 if net2 > 0 else max_fight
   ```
5. Change `    t_die = min(time_to_die(side.health, t1), max_fight)` to `    t_die = min(time_to_die(side.health, t1, net1), max_fight)`.
6. Replace
   ```python
           h_die = min(time_to_die(side.health + side.heal_budget, t1 + heal_time), max_fight)
   ```
   with
   ```python
           rate1 = (net1 * t1 + net1_heal * heal_time) / (t1 + heal_time)
           h_die = min(time_to_die(side.health + side.heal_budget, t1 + heal_time, rate1), max_fight)
   ```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, 2 of the 3 tests in `tests/test_roots_while_healing.py` fail with `AssertionError`. That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), with hunks in file order.

## Done when
`.venv/Scripts/python -m pytest tests/test_roots_while_healing.py tests/test_root_break.py tests/test_outnumbered.py tests/test_duel.py tests/test_self_heal.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`.
