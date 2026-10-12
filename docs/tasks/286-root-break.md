# Task #286: damage breaks Entangling Roots on the target being damaged

Make `tests/test_root_break.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `config/assumptions.toml`, `src/wowforever/schema.py`, `src/wowforever/classes/druid.py`, `src/wowforever/pvp/duel.py` and `src/wowforever/pvp/class_pvp.py`. The test docstring has the hand-worked numbers.

## Why
The duel model counts a root fully even on the opponent the side is damaging. In Forever, damage breaks Roots past a threshold, and Improved Entangling Roots raises the threshold by 25/50/75%. The base threshold becomes an assumption: 10% of the rooted target's health.

## Change
1. **`config/assumptions.toml`:** append
   ```toml

   [roots_break_health_pct]
   value = 10
   options = [10, 0]
   why = "Forever's Entangling Roots keeps 'Damage caused may interrupt the effect', and Improved Entangling Roots lets victims take 25/50/75% more damage before it breaks, so there is a damage threshold; no public source gives it. 10% of the rooted target's maximum health is AzerothCore's threshold; 0 = roots never break (#286)."
   source = "Entangling Roots and Improved Entangling Roots rank texts, build 1.60.1.70338; azerothcore-wotlk issue #18787 (CountPctFromMaxHealth(10)); Blizzard on TBC Classic: a random range of damage, not a fixed amount"
   tested = ""
   talents = ["Improved Entangling Roots"]
   ```
2. **`src/wowforever/schema.py`, `EFFECT_KINDS`:** after the `"targets",` line add
   ```python
       "break_threshold_pct",  # % more damage a control's target takes before the control breaks
   ```
3. **`src/wowforever/classes/druid.py`:**
   - In `TALENT_EFFECTS`, just before the `"Overgrowth": (` entry, add
     ```python
         "Improved Entangling Roots": (
             EffectRule("break_threshold_pct", r"can take up to (\d+)% more damage without interrupting", ("Entangling Roots",)),
         ),
     ```
   - In `UNMODELED`, delete the `"Improved Entangling Roots": ...` line.
4. **`src/wowforever/pvp/duel.py`:**
   - In `MageSide`, after the `root_targets` field add
     ```python
         root_break_health: float = 0.0  # damage that breaks its root, share of the target's health; 0 = never (#286)
         root_duration: float = 0.0  # seconds one root lasts unbroken
     ```
   - Just before `def _kiting_seconds(`, add
     ```python
     def root_hold(side: MageSide, kit: Kit) -> float:
         """Share of the side's root time that holds on `kit` while the side damages it (#286): the root breaks
         once the side has dealt root_break_health x kit health. 1 when the side's roots don't break."""
         if side.root_break_health <= 0 or side.root_duration <= 0 or side.dps <= 0:
             return 1.0
         return min(1.0, side.root_break_health * kit.health / (side.dps * side.root_duration))


     def _held(side: MageSide, kit: Kit) -> MageSide:
         """`side` with its roots scaled by root_hold against `kit`, the target it's damaging."""
         return dataclasses.replace(side, root=side.root * root_hold(side, kit))


     ```
   - In `duel`, change `_kiting_seconds(mage, kit, c)` to `_kiting_seconds(_held(mage, kit), kit, c)`.
   - In `outnumbered`'s docstring, replace these three lines
     ```
         the attacked one too with root_targets >= 2. Phase 2: `second` alone, as in a duel. Healing happens
         in phase 1 and counts only if the score rises. mage_uptime and opponent_uptime are phase 1's,
         the latter for `first`."""
     ```
     with
     ```
         the attacked one too with root_targets >= 2 until damage breaks them (#286). Phase 2: `second`
         alone, as in a duel. Healing happens in phase 1 and counts only if the score rises. mage_uptime
         and opponent_uptime are phase 1's, the latter for `first`."""
     ```
   - In `outnumbered`, change `root=side.root if side.root_targets >= 2 else 0.0` to `root=side.root * root_hold(side, first) if side.root_targets >= 2 else 0.0`, and change `net2 = incoming(second, side)[0] - barrier([second])` to `net2 = incoming(second, _held(side, second))[0] - barrier([second])`.
5. **`src/wowforever/pvp/class_pvp.py`, `class_side`:**
   - After the `extra = sum(...)` statement (two lines), add
     ```python
         # damage breaks roots past a share of the target's health, raised by talents (#286)
         tougher = sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                       for e in t.effects if e.kind == "break_threshold_pct" and roots & set(e.applies_to))
         root_durations = [c.duration for c in controls if c.kind == "root"]
     ```
   - In the `MageSide(...)` call, after `root_targets=1 + int(extra),` add
     ```python
             root_break_health=assumptions["roots_break_health_pct"] / 100 * (1 + tougher / 100),
             root_duration=max(root_durations, default=0.0),
     ```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_root_break.py` fails at collection with `ImportError` (`root_hold`). That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above, with each file's hunks in file order.

## Done when
`.venv/Scripts/python -m pytest tests/test_root_break.py tests/test_outnumbered.py tests/test_duel.py tests/test_class_pvp.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`.
