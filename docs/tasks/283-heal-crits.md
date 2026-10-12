# Task #283: heal crits in self-healing

Make `tests/test_hot_heals.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/classes/druid.py` and `src/wowforever/pvp/class_pvp.py`. The test docstring has the hand-worked numbers.

## Why
Self-healing counts direct heals at their average amount. Direct heals crit like spells (150%), and Improved Regrowth adds up to 50% crit chance to Regrowth.

## Change
1. **`src/wowforever/classes/druid.py`:**
   - After the `"Gift of the Earthmother"` entry in `TALENT_EFFECTS`, add
     ```python
         "Improved Regrowth": (
             EffectRule("crit_chance", r"critical effect chance of your Regrowth spell by (\d+(?:\.\d+)?)%", ("Regrowth",)),
         ),
     ```
   - In `UNMODELED`, delete the `"Improved Regrowth": ...` line.
2. **`src/wowforever/pvp/class_pvp.py`:**
   - Change the import `from wowforever.calc.ev import GCD_SECONDS` to `from wowforever.calc.ev import BASE_CRIT_BONUS_PCT, GCD_SECONDS`.
   - In `HealMods`, after the `gcd` field add `crit: float = 0.0          # more crit chance, percentage points`.
   - In `heal_modifiers`: add `"crit"` to the `dict.fromkeys(...)` tuple (after `"gcd"`), and add this branch after the `healing_pct` branch, before the `elif effect.kind in named` branch:
     ```python
                 elif effect.kind == "crit_chance" and ("all" in effect.applies_to or spell.name in effect.applies_to):
                     totals["crit"] += value
     ```
     In its docstring, after "(Moonglow's school-wide cut is for damaging spells)" insert ". Crit chance comes from effects targeting \"all\" or the heal by name".
   - Change `_heal` to take the base crit and apply it to the direct part:
     ```python
     def _heal(spell: SpellRank, spell_power: float, mods: HealMods, crit_pct: float) -> tuple[float, float, float, float]:
         """(direct healing, periodic healing, seconds, mana) of one cast after talents; direct healing crits (#283)."""
         crit = min(100.0, crit_pct + mods.crit) / 100
         direct = (((spell.heal_min + spell.heal_max) / 2 + spell.heal_coefficient * spell_power) * (1 + mods.direct_pct / 100)
                   * (1 + crit * BASE_CRIT_BONUS_PCT / 100))
     ```
     (the rest of `_heal` stays the same).
   - In `heal_capacity`, after the `sp = ...` line add
     ```python
         # a melee row's crit is melee crit; its spell crit isn't modeled (#283)
         crit_pct = getattr(row, "crit_pct", 0.0) if hasattr(row, "spell_power") else 0.0
     ```
     and pass `crit_pct` as the last argument of all three `_heal(...)` calls. In its docstring, after "If the opening costs more than that mana, it scales down to fit." insert " Direct healing crits at the row's crit plus crit talents (#283)."

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, 7 tests in `tests/test_hot_heals.py` fail with `AssertionError` or `AttributeError`, and 2 pass. That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above, with each file's hunks in file order.

## Done when
`.venv/Scripts/python -m pytest tests/test_hot_heals.py tests/test_heal_talents.py tests/test_self_heal.py tests/test_class_pvp.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`.
