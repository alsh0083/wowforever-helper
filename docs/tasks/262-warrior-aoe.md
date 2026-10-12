# Task #262 (warrior slice): warrior AoE pulls

Make `tests/test_warrior_aoe.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `config/warrior.toml`, `src/wowforever/classes/warrior_rotation.py` and `src/wowforever/melee_scenarios.py`. The test docstring describes the rules.

## Why
#263 gave every class an AoE pulls score. Melee classes still clear a pack one mob at a time. This slice teaches the warrior rotation to fight a pack: `warrior_rotation(..., pack=N)` sums damage over N mobs, and `melee_scenarios.aoe` runs it with `pack=3`.

## Change
1. **`config/warrior.toml`:** append
   ```toml

   # AoE pulls (#262). Cleave hits this many targets (Classic "the target and his nearest ally"; Forever's
   # data has no target count). Whirlwind and Thunder Clap use the data's MaxTargets (4).
   cleave_targets = 2
   # Sweeping Strikes: "Your next 5 melee attacks strike an additional nearby opponent" (rank text)
   sweeping_strikes_attacks = 5
   ```
2. **`src/wowforever/classes/warrior_rotation.py`:**
   - In the module docstring, replace
     ```
     Not modeled yet: Fury dual wield and Bloodthirst, Flurry, Execute below 20%, Overpower procs, Slam,
     Sweeping Strikes' second target, and Rage from damage taken.
     ```
     with
     ```
     Against a pack (`pack` > 1, AoE pulls #262) Whirlwind and Thunder Clap hit up to their data
     MaxTargets, Cleave replaces Heroic Strike, and Sweeping Strikes gives its attacks to a second mob.

     Not modeled yet: Fury dual wield and Bloodthirst, Flurry, Execute below 20%, Overpower procs, Slam,
     and Rage from damage taken.
     ```
   - In `WarriorRotation`, after the `abilities` field add
     ```python
         aoe: tuple[str, ...] = ()      # abilities that hit more than one mob of the pack
         parts: tuple[tuple[str, float], ...] = ()   # each ability's DPS over the pack, before Death Wish
     ```
   - Replace the end of the `warrior_rotation` signature and its docstring
     ```python
                          ranks: Mapping[int, int], target: Target) -> WarriorRotation:
         """Sustained DPS against `target` with the warrior's talents `ranks`."""
     ```
     with
     ```python
                          ranks: Mapping[int, int], target: Target, *, pack: int = 1) -> WarriorRotation:
         """Sustained DPS against `target` with the warrior's talents `ranks`; with `pack` > 1, the damage
         summed over a pack of that many such mobs (#262)."""
     ```
   - In `strike`, after the `base = (normalized if ...)` line add
     ```python
             if not spell.weapon_hits:          # flat damage (Thunder Clap)
                 base = (spell.min_damage + spell.max_damage) / 2
     ```
   - Replace everything from the line `    rage, yellow, used, crits = income, 0.0, [], 0.0` to the end of the file with
     ```python
         def targets(spell: SpellRank) -> int:
             return min(pack, spell.max_targets) if spell.max_targets > 0 else 1

         rage, yellow, used, crits, aoe, parts = income, 0.0, [], 0.0, [], []
         single, attacks = 0.0, swings      # one target's ability damage and attacks per second (Sweeping Strikes)
         names = ("Mortal Strike", "Whirlwind") + (("Thunder Clap",) if pack > 1 else ())
         plan = [s for s in map(learned, names)
                 if s is not None and s.cooldown > 0 and (s.name != "Mortal Strike" or taken(s.name))]
         if pack > 1:   # against a pack, the most damage per Rage over all the mobs goes first
             plan.sort(key=lambda s: -strike(s) * targets(s) / cost(s) if cost(s) else float("-inf"))
         for spell in plan:
             name = spell.name
             rate = min(1 / spell.cooldown, rage / cost(spell)) if cost(spell) else 1 / spell.cooldown
             n = targets(spell)
             rage -= rate * cost(spell)
             yellow += rate * strike(spell) * n
             parts.append((name, rate * strike(spell) * n))
             single, attacks = single + rate * strike(spell), attacks + rate
             crits += rate * n * land_chance(attacker, target) * yellow_crit_chance(attacker, target,
                                                                                    total("crit_chance", name))
             used.append(name)
             if n > 1 and rate > 0:
                 aoe.append(name)

         sweeping = learned("Sweeping Strikes") if pack > 1 and taken("Sweeping Strikes") else None
         sweep_rate = 0.0
         if sweeping is not None and sweeping.cooldown > 0 and rage > 0:
             sweep_rate = min(1 / sweeping.cooldown, rage / cost(sweeping)) if cost(sweeping) else 1 / sweeping.cooldown
             rage -= sweep_rate * cost(sweeping)

         # against a pack, Cleave takes Heroic Strike's place on the next swing
         heroic = learned("Cleave" if pack > 1 else "Heroic Strike")
         hs_rate = 0.0
         if heroic is not None and rage > 0:
             # each Heroic Strike costs its Rage plus the Rage its white swing would have made
             n = min(pack, c["cleave_targets"]) if heroic.name == "Cleave" else 1
             hs_rate = min(swings, rage / (cost(heroic) + rage_per_swing))
             yellow += hs_rate * (strike(heroic) * n - swing_ev)
             parts.append((heroic.name, hs_rate * (strike(heroic) * n - swing_ev)))
             single += hs_rate * (strike(heroic) - swing_ev)
             crits += hs_rate * n * land_chance(attacker, target) * yellow_crit_chance(attacker, target)
             used.append(heroic.name)
             if n > 1:
                 aoe.append(heroic.name)
         white = swings * swing_ev
         if sweep_rate > 0:
             # its attacks also hit a second mob: an average attack each, swings and abilities alike
             extra = sweep_rate * c["sweeping_strikes_attacks"] * (white + single) / attacks
             yellow += extra
             parts.append(("Sweeping Strikes", extra))
             used.append("Sweeping Strikes")
             aoe.append("Sweeping Strikes")

         # Deep Wounds: every crit bleeds a share of the weapon's average damage
         crits += (swings - hs_rate) * land_chance(attacker, target) * yellow_crit_chance(attacker, target)
         bleed = crits * total("dot_pct", "@crit") / 100 * avg_weapon
         yellow += bleed

         return WarriorRotation(dps=(white + yellow) * death_wish, white_dps=white * death_wish,
                                yellow_dps=yellow * death_wish, rage_per_second=income, abilities=tuple(used),
                                aoe=tuple(aoe), parts=tuple(parts))
     ```
3. **`src/wowforever/melee_scenarios.py`:**
   - In `Output`, after the `fallback_dps` field add
     ```python
         aoe: tuple[str, ...] = ()   # abilities that hit several mobs of a pack (#262)
     ```
   - In `rotation_output`, change `melee: bool | None = None) -> Output:` to `melee: bool | None = None, pack: int = 1) -> Output:`, and replace the docstring's last line `    by default it follows the tree with most points."""` with
     ```python
         by default it follows the tree with most points. `pack` > 1 sums damage over that many mobs for
         classes whose AoE abilities are modeled (warrior, #262); the others stay single target."""
     ```
   - In the warrior branch of `rotation_output`, replace
     ```python
             r = warrior_rotation(stats, spells, cls, ranks, target)
             return Output(r.dps, 0.0, r.dps)
     ```
     with
     ```python
             r = warrior_rotation(stats, spells, cls, ranks, target, pack=pack)
             return Output(r.dps, 0.0, r.dps, r.aoe)
     ```
   - In `aoe`, replace the docstring lines
     ```
         (caster.aoe_pull, #260); the others clear the pack with their single-target rotation until their AoE
         abilities are modeled (#262)."""
     ```
     with
     ```
         (caster.aoe_pull, #260); the others run their rotation against the pack (rotation_output's `pack`,
         #262), single target where their AoE abilities aren't modeled yet."""
     ```
     and replace its last two lines
     ```python
         dps = rotation_output(class_name, stats, spells, cls, ranks, Target(0, armor)).dps
         return pack * mob_hp / dps, "single target"
     ```
     with
     ```python
         out = rotation_output(class_name, stats, spells, cls, ranks, Target(0, armor), pack=pack)
         return pack * mob_hp / out.dps, ", ".join(out.aoe) or "single target"
     ```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_warrior_aoe.py` fails with `TypeError` (`pack` is not an argument yet). That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above, with each file's hunks in file order. For the big replacement in step 2, a hunk whose `-` lines are the old lines from `    rage, yellow, used, crits = income, 0.0, [], 0.0` to the end of the file works; copy them from the file exactly.

## Done when
`.venv/Scripts/python -m pytest tests/test_warrior_aoe.py tests/test_warrior_engine.py tests/test_aoe_score.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`. Do not run the slow tests.
