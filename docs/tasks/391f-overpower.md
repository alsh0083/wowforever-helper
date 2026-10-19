# Task #391 (part 4): Overpower after dodges

Make `tests/test_overpower.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/warrior_rotation.py`. Run the test file, then the fast suite
  once. Warrior regression pins (`tests/test_kit_stats.py`, opponent kits, `tests/test_dungeon_mana.py`,
  `tests/test_warrior_aoe.py`, `tests/test_execute.py`, `tests/test_class_engine.py`) may move; Claude re-derives
  them.
- Before you start, the tests in `tests/test_overpower.py` fail with an ImportError.

## Why
Overpower is usable after the target dodges and can't be dodged itself (its description). Best effort (owner OK
2026-10-16): it goes out as often as the target dodges the warrior's attacks, at most once per its cooldown, with
the Rage left after the cooldown abilities and before Heroic Strike. A build with Bloodthirst stays in Berserker
Stance and skips it (Overpower needs Battle Stance).

## Step 1: add this function directly before `def warrior_rotation(`
```python
def overpower_rate(attacks: float, dodge: float, cooldown: float, rage: float, cost: float) -> float:
    """Overpowers per second (#391): one per dodged attack, at most one per cooldown, as Rage allows."""
    rate = min(attacks * dodge, 1 / cooldown if cooldown > 0 else float("inf"))
    return min(rate, rage / cost) if cost > 0 else rate
```

## Step 2: in `warrior_rotation`
Directly before the line `    sweeping = learned("Sweeping Strikes") if pack > 1 and taken("Sweeping Strikes") else None` add:
```python
    overpower = learned("Overpower")
    if overpower is not None and rage > 0 and not taken("Bloodthirst"):
        # after a dodge, and it can't be dodged (#391); Fury's Berserker Stance can't use it
        dodge = land_chance(attacker, target, can_dodge=False) - land_chance(attacker, target)
        op_rate = overpower_rate(attacks, dodge, overpower.cooldown, rage, cost(overpower))
        base = (normalized if overpower.weapon_normalized else avg_weapon + stats.attack_power / 14 * weapon[2])
        op_hit = yellow_attack(base + overpower.weapon_bonus, attacker, target, can_dodge=False,
                               crit_bonus=total("crit_chance", "Overpower"),
                               damage_pct=weapon_pct + total("damage_pct", "Overpower"), crit_damage_pct=crit_damage)
        if op_rate > 0:
            rage -= op_rate * cost(overpower)
            yellow += op_rate * op_hit
            parts.append(("Overpower", op_rate * op_hit))
            single, attacks = single + op_rate * op_hit, attacks + op_rate
            crits += op_rate * land_chance(attacker, target, can_dodge=False) * yellow_crit_chance(
                attacker, target, total("crit_chance", "Overpower"))
            used.append("Overpower")
```
In the module docstring, `Not modeled yet:` / `Overpower procs, Slam, and Rage from damage taken.` becomes
`Overpower follows dodges (#391). Not modeled yet: Slam and Rage from damage taken.` (keep lines under 110).

Nothing else changes.

## Done when
- `tests/test_overpower.py` passes; no other new failures apart from warrior pins.
