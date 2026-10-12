# Task #279: heals over time and Swiftmend in self-healing

Make `tests/test_hot_heals.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `config/assumptions.toml`, `config/pvp_self.toml`, `src/wowforever/schema.py`, `src/wowforever/classes/druid.py` and `src/wowforever/pvp/class_pvp.py`. The test docstring has the hand-worked numbers.

## Why
Self-healing (#265, #276) counts only direct heals. Rejuvenation and Regrowth's periodic part give a druid far more healing per second of casting. A healing phase now opens with each HoT once, then Swiftmend, then spends the rest of the healing mana on direct heals.

## Change
1. **`config/assumptions.toml`:** append
   ```toml

   [swiftmend_consumes_hot]
   value = false
   options = [false, true]
   why = "Forever's Swiftmend heals for the HoT's full duration and, unlike Classic's text, doesn't say it consumes the HoT; if it does, Swiftmend only front-loads healing the HoT would have given (#279)."
   source = "Swiftmend rank text, build 1.60.1.70291; Classic: 'Consumes a Rejuvenation or Regrowth effect'"
   tested = ""
   talents = ["Swiftmend"]
   ```
2. **`config/pvp_self.toml`, `[druid]`:** replace the `# self-healing in duels (#265): ...` comment line and the `heals = ...` line with
   ```toml
   # self-healing in duels (#265, #279): a healing phase opens with each of `hots` once, then `hot_burst`, then the best of `heals`; share of mana spent healing (estimate)
   heals = ["Healing Touch", "Regrowth"]
   hots = ["Rejuvenation", "Regrowth"]
   hot_burst = "Swiftmend"
   ```
   (keep `heal_mana_share = 0.5`).
3. **`src/wowforever/schema.py`, `EFFECT_KINDS`:** after the `"cooldown",` line add
   ```python
       "gcd",              # change to the global cooldown, seconds (negative = shorter)
   ```
4. **`src/wowforever/classes/druid.py`:**
   - In `TALENT_EFFECTS["Genesis"]`, add a second rule after the `damage_pct` one:
     ```python
             EffectRule("healing_pct", r"periodic damage and healing done by your spells and abilities by (\d+(?:\.\d+)?)%",
                        ("periodic",)),
     ```
   - After the `"Tranquil Spirit"` entry, add
     ```python
         "Improved Rejuvenation": (
             EffectRule("healing_pct", r"effect of your Rejuvenation spell by (\d+(?:\.\d+)?)%", ("Rejuvenation",)),
         ),
         # HoT durations only; longer Moonfire and Insect Swarm aren't modeled
         "Nature's Splendor": (
             EffectRule("duration", r"Moonfire and Rejuvenation spells by (\d+(?:\.\d+)?) sec", ("Rejuvenation",)),
             EffectRule("duration", r"your Regrowth spell by (\d+(?:\.\d+)?) sec", ("Regrowth",)),
         ),
         "Gift of the Earthmother": (
             EffectRule("gcd", r"global cooldown by (\d+(?:\.\d+)?) seconds", ("Rejuvenation", "Swiftmend", "Wild Growth"), sign=-1),
         ),
     ```
   - In `UNMODELED`, delete the `"Nature's Splendor": ...`, `"Gift of the Earthmother": ...` and `"Improved Rejuvenation": ...` lines.
5. **`src/wowforever/pvp/class_pvp.py`:**
   - Add `from dataclasses import dataclass` to the imports.
   - In the module docstring, replace `Druids heal themselves with direct heals when that helps (#265).` with `Druids heal themselves with HoTs, Swiftmend and direct heals when that helps (#265, #279).`
   - Replace the whole `heal_modifiers` function with
     ```python
     @dataclass(frozen=True)
     class HealMods:
         """Talent changes to one heal (#276, #279)."""

         cast: float = 0.0          # cast time change, s
         cost: float = 0.0          # mana cost change, %
         direct_pct: float = 0.0    # more direct healing, %
         periodic_pct: float = 0.0  # more periodic healing, %
         duration: float = 0.0      # longer HoT, s
         gcd: float = 0.0           # global cooldown change, s


     def heal_modifiers(spell: SpellRank, cls: ClassData, ranks: Mapping[int, int]) -> HealMods:
         """Talent changes to one heal (#276, #279).

         Healing % applies to both parts when it targets "all" or the heal by name, and to the periodic part only
         when it targets "periodic" (Genesis). Cast time, mana cost, duration and global cooldown come only from
         effects naming the heal (Moonglow's school-wide cut is for damaging spells)."""
         totals = dict.fromkeys(("cast", "cost", "direct_pct", "periodic_pct", "duration", "gcd"), 0.0)
         named = {"cast_time": "cast", "mana_cost_pct": "cost", "duration": "duration", "gcd": "gcd"}
         for talent_id, rank in ranks.items():
             if rank <= 0:
                 continue
             for effect in cls.talent(talent_id).effects:
                 value = effect.values[rank - 1]
                 if effect.kind == "healing_pct":
                     if "all" in effect.applies_to or spell.name in effect.applies_to:
                         totals["direct_pct"] += value
                         totals["periodic_pct"] += value
                     elif "periodic" in effect.applies_to:
                         totals["periodic_pct"] += value
                 elif effect.kind in named and spell.name in effect.applies_to:
                     totals[named[effect.kind]] += value
         return HealMods(**totals)


     def _heal(spell: SpellRank, spell_power: float, mods: HealMods) -> tuple[float, float, float, float]:
         """(direct healing, periodic healing, seconds, mana) of one cast after talents."""
         direct = ((spell.heal_min + spell.heal_max) / 2 + spell.heal_coefficient * spell_power) * (1 + mods.direct_pct / 100)
         periodic = 0.0
         if spell.periodic_heal > 0 and spell.duration > 0:
             periodic = ((spell.periodic_heal + spell.periodic_heal_coefficient * spell_power)
                         * (1 + mods.periodic_pct / 100) * (spell.duration + mods.duration) / spell.duration)
         seconds = max(GCD_SECONDS + mods.gcd, spell.cast_time + mods.cast)
         return direct, periodic, seconds, spell.mana_cost * (1 + mods.cost / 100)
     ```
   - Replace the whole `heal_capacity` function with
     ```python
     def heal_capacity(class_name: str, stats, spells: Sequence[SpellRank], cls: ClassData,
                       ranks: Mapping[int, int], *, assumptions: Assumptions | None = None) -> tuple[float, float]:
         """(healing per second while healing, mana-limited healing budget) for the class's healing phase (#265, #279).

         The phase opens with each heal in config `hots` once (direct part plus its full periodic healing: fights
         outlast the HoTs), then `hot_burst` (copies the biggest HoT's periodic healing; nothing when the
         swiftmend_consumes_hot assumption is on). The rest of mana x heal_mana_share goes to the heal in `heals`
         with the most direct healing per second. If the opening costs more than that mana, it scales down to fit.
         A spell named like a talent counts only when the talent is taken. Classes without `heals`: (0, 0)."""
         cfg = load_toml(CONFIG)[class_name]
         if "heals" not in cfg:
             return (0.0, 0.0)
         if assumptions is None:
             assumptions = Assumptions.load()
         row = build_stats(class_name, stats, cls, ranks)
         sp = getattr(row, "spell_power", 0.0)
         mana_budget = row.mana * cfg["heal_mana_share"]
         talents = {t.name: t.talent_id for t in cls.talents}

         def learned(name: str) -> SpellRank | None:
             if name in talents and ranks.get(talents[name], 0) <= 0:
                 return None
             return best_rank(spells, name, stats.level)

         amount = seconds = mana = biggest = 0.0
         for name in cfg.get("hots", []):
             spell = learned(name)
             if spell is None or spell.mana_cost <= 0 or spell.periodic_heal <= 0:
                 continue
             direct, periodic, secs, cost = _heal(spell, sp, heal_modifiers(spell, cls, ranks))
             amount, seconds, mana = amount + direct + periodic, seconds + secs, mana + cost
             biggest = max(biggest, periodic)
         burst = learned(cfg["hot_burst"]) if "hot_burst" in cfg else None
         if burst is not None and biggest > 0 and not assumptions["swiftmend_consumes_hot"]:
             amount += biggest
             seconds += _heal(burst, sp, heal_modifiers(burst, cls, ranks))[2]
         if mana > 0 and mana >= mana_budget:
             return (amount / seconds, amount * mana_budget / mana)

         best: tuple[float, float, float] | None = None
         for name in cfg["heals"]:
             spell = learned(name)
             if spell is None or spell.mana_cost <= 0 or spell.heal_max <= 0:
                 continue
             direct, _, secs, cost = _heal(spell, sp, heal_modifiers(spell, cls, ranks))
             if best is None or direct / secs > best[0] / best[1]:
                 best = (direct, secs, cost)
         if best is not None:
             filler = (mana_budget - mana) * best[0] / best[2]
             amount, seconds = amount + filler, seconds + filler * best[1] / best[0]
         return (amount / seconds, amount) if seconds > 0 else (0.0, 0.0)
     ```
   - In `class_side`, change the `heal_capacity(...)` call to pass `assumptions=assumptions`.

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_hot_heals.py` fails at collection with `KeyError: 'swiftmend_consumes_hot'`. That's expected, and step 1 fixes it. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above. For the two function replacements in step 5, a `*** Update File:` hunk whose `-` lines are the old function and whose `+` lines are the new one works; copy the old lines from the file exactly, including blank lines.

## Done when
`.venv/Scripts/python -m pytest tests/test_hot_heals.py tests/test_heal_talents.py tests/test_self_heal.py tests/test_class_pvp.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`.
