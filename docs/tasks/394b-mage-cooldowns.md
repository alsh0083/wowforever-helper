# Task #394 (cooldowns): Combustion and Presence of Mind in the sustained mage rotation

Make `tests/test_mage_cooldowns.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/mage_rotation.py`, then `src/wowforever/classes/mage.py`. Run
  the test file, then the fast suite once. Mage regression pins (`tests/test_dungeon_mana.py`, opponent kits) may
  move; Claude re-derives them.
- Before you start, `tests/test_mage_cooldowns.py` fails to import (the two new functions don't exist yet).

## Why
Combustion and Presence of Mind are three-minute cooldowns the model leaves out. Like Arcane Power, they count in
the sustained (raid) rotation, averaged over their cooldowns.

## Step 1: `src/wowforever/classes/mage_rotation.py`
1. Directly after the `frozen_lance_multiplier` function (before `def frozen_hit_gain`), add:
```python
def combustion_rule(cls) -> tuple[float, int]:
    """Combustion's (crit % per Fire hit, crits until it ends) from its rank text (#394)."""
    import re

    text = cls.talent_named("Combustion").rank_text[-1]
    step = re.search(r"critical strike chance with Fire damage spells by (\d+(?:\.\d+)?)%", text).group(1)
    limit = re.search(r"until you have caused (\d+) non-periodic critical strikes", text).group(1)
    return float(step), int(limit)


def combustion_extra_crits(p: float, hit: float, step: float, limit: int) -> float:
    """Expected extra crit chance summed over the casts while Combustion lasts (#394). Cast i (from 0) crits with
    min(1, p + step x i) instead of p; a cast crits with `hit` x that chance, and Combustion ends after `limit`
    crits. Exact over the number of crits so far, cut off once it has ended with certainty (or after 200 casts)."""
    active = [1.0] + [0.0] * (limit - 1)    # chance of being on c crits, Combustion still up
    extra, i = 0.0, 0
    while sum(active) > 1e-12 and i < 200:
        chance = min(1.0, p + step * i)
        extra += sum(active) * (chance - p)
        q = hit * chance
        nxt = [0.0] * limit
        for c, pr in enumerate(active):
            nxt[c] += pr * (1 - q)
            if c + 1 < limit:
                nxt[c + 1] += pr * q
        active, i = nxt, i + 1
    return extra


```
2. In `rotation`, directly before the final `    return Rotation(` statement, add:
```python
    if sustained and taken("Presence of Mind") > 0:
        # one instant cast per cooldown: a GCD of filler time for the filler or Pyroblast, whichever gains more (#394)
        pom = best_rank(char.spells, "Presence of Mind", char.level)
        options = [(filler, filler_mods)]
        pyro = best_rank(char.spells, "Pyroblast", char.level) if taken("Pyroblast") > 0 else None
        if pyro is not None:
            options.append((pyro, mods_for(pyro)))
        if pom is not None and pom.cooldown > 0:
            spell, mods = max(options, key=lambda o: ev_of(*o))
            dps += (ev_of(spell, mods) - filler_dps * GCD_SECONDS) / pom.cooldown
            mana_per_second += cost(spell, mods) / pom.cooldown
    if sustained and taken("Combustion") > 0 and "fire" in filler.schools:
        # Fire crit rising per cast until a few crits, once per cooldown (#394)
        combustion = best_rank(char.spells, "Combustion", char.level)
        if combustion is not None and combustion.cooldown > 0:
            step, limit = combustion_rule(char.cls)
            plus = replace(filler_mods, crit_chance_bonus=filler_mods.crit_chance_bonus + 1.0)
            per_crit = (ev_of(filler, plus) - ev_of(filler, filler_mods)) / 0.01
            extra = combustion_extra_crits(min(1.0, crit), hit, step / 100.0, limit)
            dps += extra * per_crit / combustion.cooldown
```

## Step 2: `src/wowforever/classes/mage.py`
In `UNMODELED`, the two lines
```python
    "Presence of Mind": "conditional instant cast, v1",
```
and
```python
    "Combustion": "not modeled yet",
```
become
```python
    "Presence of Mind": "handled in mage_rotation",
```
and
```python
    "Combustion": "handled in mage_rotation",
```

Nothing else changes.

## Done when
- `tests/test_mage_cooldowns.py` passes; no other new failures apart from mage pins.
