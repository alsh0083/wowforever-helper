# Task #262 (rogue slice): Blade Flurry against a pack

Make `tests/test_rogue_aoe.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `src/wowforever/classes/rogue_rotation.py` and `src/wowforever/melee_scenarios.py`. The test docstring has the rule.

## Why
The warrior slice of #262 added `pack` to `rotation_output`. Rogues still clear a pack one mob at a time, but Blade Flurry makes every attack hit a second mob for 15 s out of every 120 s.

## Change
1. **`src/wowforever/classes/rogue_rotation.py`:**
   - In the module docstring, replace
     ```
     Not modeled yet: poisons, Backstab (needs the main-hand weapon type), Hack and Slash extra
     attacks, and Blade Flurry's second target.
     """
     ```
     with
     ```
     Against a pack (`pack` > 1, AoE pulls #262), Blade Flurry's attacks also hit a second mob for its
     share of the cooldown (15 s of 120 s), averaged like its haste.

     Not modeled yet: poisons, Backstab (needs the main-hand weapon type) and Hack and Slash extra attacks.
     """
     ```
   - In `RogueRotation`, after the `cycles_per_second` field add
     ```python
         aoe: tuple[str, ...] = ()  # abilities that hit more than one mob of the pack (#262)
     ```
   - Replace the end of the `rogue_rotation` signature and its docstring
     ```python
                        ranks: Mapping[int, int], target: Target) -> RogueRotation:
         """Sustained DPS against `target` with the rogue's talents `ranks`."""
     ```
     with
     ```python
                        ranks: Mapping[int, int], target: Target, *, pack: int = 1) -> RogueRotation:
         """Sustained DPS against `target` with the rogue's talents `ranks`; with `pack` > 1, the damage
         summed over a pack of that many such mobs (#262)."""
     ```
   - Replace the final `return RogueRotation(...)` statement (two lines) with
     ```python
         aoe: tuple[str, ...] = ()
         if pack > 1 and taken("Blade Flurry"):
             bf = c["blade_flurry"]
             share = bf["duration"] / bf["cooldown"]
             white, yellow, aoe = white * (1 + share), yellow * (1 + share), ("Blade Flurry",)
         return RogueRotation(dps=white + yellow, white_dps=white, yellow_dps=yellow, builder=builder.name,
                              energy_per_second=energy, cycles_per_second=cycles, aoe=aoe)
     ```
2. **`src/wowforever/melee_scenarios.py`, `rotation_output`:**
   - In the rogue branch, replace
     ```python
             r = rogue_rotation(stats, spells, cls, ranks, target)
             return Output(r.dps, 0.0, r.dps)
     ```
     with
     ```python
             r = rogue_rotation(stats, spells, cls, ranks, target, pack=pack)
             return Output(r.dps, 0.0, r.dps, r.aoe)
     ```
   - In the docstring, change `classes whose AoE abilities are modeled (warrior, #262); the others stay single target."""` to `classes whose AoE abilities are modeled (warrior and rogue, #262); the others stay single target."""`.

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_rogue_aoe.py` fails with `TypeError` (`pack` is not an argument of `rogue_rotation`). That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above, with each file's hunks in file order.

## Done when
`.venv/Scripts/python -m pytest tests/test_rogue_aoe.py tests/test_rogue_rotation.py tests/test_aoe_score.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`. Do not run the slow tests.
