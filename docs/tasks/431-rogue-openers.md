# Task #431 (rogue openers): Ambush, Initiative and Remorseless Attacks for questing kills

Make `tests/test_rogue_openers.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit in this order: `src/wowforever/melee_scenarios.py`, `src/wowforever/classes/rogue.py`,
  `src/wowforever/classes/rogue_rotation.py`. Run the test file, then the fast suite once. Rogue regression pins may
  move; Claude re-derives them.
- Before you start, `tests/test_rogue_openers.py` fails.

## Why
Questing kills are short, so damage dealt once per fight matters there: a rogue opens from stealth with Ambush
(with a dagger), Initiative adds a combo point, and Remorseless Attacks crits the first attack after a kill. The
Output carries this as `opener_damage`, which questing takes off the mob's health. Dungeon and raid ignore it.

## Step 1: `src/wowforever/melee_scenarios.py`
1. In `class Output`, after the `alternatives` field (and its comment line), add:
```python
    opener_damage: float = 0.0   # damage once per fight on top of the rotation (questing openers, #431)
```
2. In `questing_kills_per_hour`, the line `    kill = q.mob_hp / out.dps` becomes
```python
    kill = max(0.0, q.mob_hp - out.opener_damage) / out.dps     # the opener takes its share first (#431)
```

## Step 2: `src/wowforever/classes/rogue.py`
1. At the end of `TALENT_EFFECTS` (directly before its closing `}`), add:
```python
    "Remorseless Attacks": (
        EffectRule("crit_chance", r"gives you a (\d+(?:\.\d+)?)% increased critical strike chance on your next",
                   ("@after_kill",)),
    ),
    "Initiative": (
        EffectRule("proc_chance", r"a (\d+(?:\.\d+)?)% chance to add an additional combo point to your target",
                   ("@initiative",)),
    ),
```
2. Delete the two `UNMODELED` lines for `"Remorseless Attacks"` and `"Initiative"`.
3. In `output`, the line `    return Output(r.dps, 0.0, r.dps, r.aoe)` becomes
   `    return Output(r.dps, 0.0, r.dps, r.aoe, opener_damage=r.opener_damage)`.

## Step 3: `src/wowforever/classes/rogue_rotation.py`
1. In `class RogueRotation`, after the `poison_dps` field, add:
```python
    opener_damage: float = 0.0   # once per kill: Ambush, Initiative, Remorseless Attacks (#431)
```
2. The builder loop
```python
    builder_ev = 0.0
    for weapon in hands:
        norm = (weapon[0] + weapon[1]) / 2 + stats.attack_power / 14 * speed
        base = (norm + builder.weapon_bonus) * (builder.weapon_pct / 100 if builder.weapon_pct else 1)
        builder_ev += yellow_attack(base, attacker, target, crit_bonus=crit_bonus,
                                    damage_pct=total("damage_pct", builder.name),
                                    crit_damage_pct=total("crit_damage_pct", builder.name),
                                    dodge_reduction=dr)
```
   becomes
```python
    def strike(spell: SpellRank, spell_speed: float, weapons, extra_crit: float = 0.0) -> float:
        """Expected damage of `spell` hitting with each of `weapons` (#431: also Ambush, and Remorseless' crit)."""
        out = 0.0
        for weapon in weapons:
            norm = (weapon[0] + weapon[1]) / 2 + stats.attack_power / 14 * spell_speed
            base = (norm + spell.weapon_bonus) * (spell.weapon_pct / 100 if spell.weapon_pct else 1)
            out += yellow_attack(base, attacker, target, crit_bonus=total("crit_chance", spell.name) + extra_crit,
                                 damage_pct=total("damage_pct", spell.name),
                                 crit_damage_pct=total("crit_damage_pct", spell.name), dodge_reduction=dr)
        return out

    builder_ev = strike(builder, speed, hands)
    # once per kill (#431): with a dagger, Ambush from stealth replaces the first builder and Initiative's combo
    # point saves another; Remorseless Attacks crits the first attack after a kill
    after_kill = total("crit_chance", "@after_kill")
    ambush = learned("Ambush") if backstab else None
    opener = 0.0
    if ambush is not None:
        opener = (strike(ambush, c["normalized_speed"]["dagger"], [stats.main_hand], after_kill) - builder_ev
                  + total("proc_chance", "@initiative") / 100 * builder_ev)
    elif after_kill > 0:
        opener = strike(builder, speed, hands, after_kill) - builder_ev
```
   (keep the `crit_bonus = total("crit_chance", builder.name)` line above it: later lines use `crit_bonus`).
3. In the final `return RogueRotation(...)` call, add `opener_damage=opener` after `poison_dps=poison_dps`.

Nothing else changes.

## Done when
- `tests/test_rogue_openers.py` passes; no other new failures apart from rogue pins.
