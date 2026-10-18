# Task #391 (part 3): Execute in the last 20% of the fight

Make `tests/test_execute.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `config/warrior.toml` first, then `src/wowforever/classes/warrior_rotation.py`. Run the test
  file, then the fast suite once. Warrior regression pins (`tests/test_kit_stats.py`, opponent kits,
  `tests/test_dungeon_mana.py`, `tests/test_warrior_aoe.py`, `tests/test_fury_dual_wield.py` white checks,
  `tests/test_class_engine.py`) may move; Claude re-derives them.
- Before you start, the tests in `tests/test_execute.py` fail with an ImportError.

## Why
Execute is only usable at or below 20% health. Its data: 600 damage (SpellEffect 20662 effect 0) and each extra
point of Rage turned into 10 more (its description, `$*10`). Best effort (owner OK 2026-10-16): in the execute
phase (20% of a steady fight, as for the execute-range talents, #392) every point of Rage goes to Execute, one per
global cooldown, and the white swings keep going; the other 80% runs the normal rotation.

## Step 1: `config/warrior.toml`
Append:
```toml
# Execute (#391): usable at or below 20% health; 600 damage (SpellEffect 20662 effect 0) plus 10 per extra Rage
# (description "$*10"); counted for that share of the fight with all Rage going to it
execute = { health_pct = 20.0, base = 600.0, per_rage = 10.0 }
```

## Step 2: `src/wowforever/classes/warrior_rotation.py`
1. Add `from wowforever.calc.ev import GCD_SECONDS` above `from wowforever.melee_stats import MeleeStats`.
2. Add this function directly before `def warrior_rotation(`:
```python
def execute_casts(income: float, cost: float, gcd: float) -> tuple[float, float]:
    """(Executes per second, extra Rage per Execute) when all Rage goes to Execute, one per global cooldown (#391)."""
    rate = min(1 / gcd, income / cost) if cost > 0 else 1 / gcd
    return rate, max(0.0, income / rate - cost) if rate > 0 else 0.0
```
3. Replace the final `return WarriorRotation(...)` statement (the three lines from `    return WarriorRotation(dps=(white + yellow) * death_wish,`) with:
```python
    dps = white + yellow
    execute = learned("Execute")
    if execute is not None and pack == 1:      # single target: a pack dies unevenly
        # the execute phase: every point of Rage into Execute, white swings unchanged (#391)
        ex = c["execute"]
        rate, extra = execute_casts(income, cost(execute), GCD_SECONDS)
        hit = yellow_attack(ex["base"] + ex["per_rage"] * extra, attacker, target,
                            crit_bonus=total("crit_chance", "Execute"),
                            damage_pct=weapon_pct + total("damage_pct", "Execute"), crit_damage_pct=crit_damage)
        share = ex["health_pct"] / 100
        dps = (1 - share) * dps + share * (white + rate * hit)
        used.append("Execute")
    return WarriorRotation(dps=dps * death_wish, white_dps=white * death_wish,
                           yellow_dps=(dps - white) * death_wish, rage_per_second=income, abilities=tuple(used),
                           aoe=tuple(aoe), parts=tuple(parts))
```
4. Module docstring: remove `Execute below 20%, ` from the "Not modeled yet" list and add the sentence
   `Execute takes all Rage in the last 20% of the fight (#391).` before `Not modeled yet:` (keep lines under 110).

Nothing else changes.

## Done when
- `tests/test_execute.py` passes; no other new failures apart from warrior pins.
