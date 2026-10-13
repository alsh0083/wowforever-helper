# Task #262 (shaman slice): Fire Nova for Enhancement against a pack

Make `tests/test_shaman_aoe.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/classes/shaman_rotation.py` and `src/wowforever/melee_scenarios.py`. The test docstring has the rule.

## Why
The warrior and rogue slices of #262 added `pack` to `rotation_output`. Enhancement shamans still clear a pack one mob at a time. Fire Nova hits every mob on a 10 s cooldown.

## Change
1. **`src/wowforever/classes/shaman_rotation.py`:**
   - In the module docstring, replace
     ```
     Not modeled yet: Stormstrike's Nature-damage debuff, Maelstrom Weapon's cheaper Lightning Bolt,
     Lightning Shield orbs, totems, and mana (shocks are the main cost).
     ```
     with
     ```
     Against a pack (`pack` > 1, AoE pulls #262) Fire Nova goes out on cooldown and hits every mob, rolled
     like Earth Shock.

     Not modeled yet: Stormstrike's Nature-damage debuff, Maelstrom Weapon's cheaper Lightning Bolt,
     Lightning Shield orbs, totems, and mana (shocks are the main cost).
     ```
   - In `EnhancementRotation`, after the `spell_dps` field add
     ```python
         aoe: tuple[str, ...] = ()   # spells that hit more than one mob of the pack (#262)
     ```
   - Replace the end of the `enhancement_rotation` signature and its docstring
     ```python
                              ranks: Mapping[int, int], target: Target) -> EnhancementRotation:
         """Sustained Enhancement DPS against `target` with the shaman's talents `ranks`."""
     ```
     with
     ```python
                              ranks: Mapping[int, int], target: Target, *, pack: int = 1) -> EnhancementRotation:
         """Sustained Enhancement DPS against `target` with the shaman's talents `ranks`; with `pack` > 1, the
         damage summed over a pack of that many such mobs (#262)."""
     ```
   - Replace everything from the line `    spell_dps = 0.0` to the end of the file with
     ```python
         spell_dps = 0.0
         hit = 1 - miss_chance(level, level + target.level_diff, stats.hit_pct) / 100
         spell_crit = min(1.0, (stats.crit_pct + total("crit_chance", "all")) / 100)
         shock = best_rank(spells, "Earth Shock", level)
         if shock is not None and shock.cooldown > 0:
             avg = (shock.min_damage + shock.max_damage) / 2 * (1 + total("damage_pct", "Earth Shock") / 100)
             spell_dps = hit * avg * (1 + spell_crit * 0.5) / max(shock.cooldown + total("cooldown", "Earth Shock"), 1.5)
         nova = best_rank(spells, "Fire Nova", level) if pack > 1 else None
         aoe: tuple[str, ...] = ()
         if nova is not None and nova.min_damage > 0:
             avg = (nova.min_damage + nova.max_damage) / 2 * (1 + total("damage_pct", "Fire Nova") / 100)
             spell_dps += hit * avg * (1 + spell_crit * 0.5) * pack / max(nova.cooldown + total("cooldown", "Fire Nova"), 1.5)
             aoe = ("Fire Nova",)
         return EnhancementRotation(dps=white + yellow + spell_dps, white_dps=white, yellow_dps=yellow, spell_dps=spell_dps,
                                    aoe=aoe)
     ```
2. **`src/wowforever/melee_scenarios.py`, `rotation_output`:**
   - In the hybrid branch, replace
     ```python
                     r = enhancement_rotation(stats.melee, spells, cls, ranks, target)
                 return Output(r.dps, 0.0, r.dps)
     ```
     with
     ```python
                     r = enhancement_rotation(stats.melee, spells, cls, ranks, target, pack=pack)
                 return Output(r.dps, 0.0, r.dps, getattr(r, "aoe", ()))
     ```
   - In the docstring, replace the line `    classes whose AoE abilities are modeled (warrior and rogue, #262); the others stay single target."""` with
     ```python
         classes whose AoE abilities are modeled (warrior, rogue and Enhancement shaman, #262); the others stay
         single target."""
     ```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_shaman_aoe.py` fails with `TypeError` (`pack` is not an argument of `enhancement_rotation`). That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above, with each file's hunks in file order.

## Done when
`.venv/Scripts/python -m pytest tests/test_shaman_aoe.py tests/test_aoe_score.py tests/test_rogue_aoe.py tests/test_warrior_aoe.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`. Do not run the slow tests.
