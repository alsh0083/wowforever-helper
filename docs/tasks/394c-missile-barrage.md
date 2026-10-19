# Task #394 (Missile Barrage): free, half-length Arcane Missiles procs

Make `tests/test_missile_barrage.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/mage_rotation.py`, then `src/wowforever/classes/mage.py`. Run
  the test file, then the fast suite once. Mage regression pins may move; Claude re-derives them.
- Before you start, `tests/test_missile_barrage.py` fails to import (`missile_barrage_rule` doesn't exist yet).

## Why
Missile Barrage (deep Arcane builds) makes the next Arcane Missiles half as long and free. Its proc chance depends
on the spell that procs it, so the rotation reads it per spell from the rank text.

## Step 1: `src/wowforever/classes/mage_rotation.py`
1. Directly after the `combustion_extra_crits` function (before `def frozen_hit_gain`), add:
```python
def missile_barrage_rule(cls, rank: int) -> dict[str, float]:
    """Missile Barrage's proc chance (%) at `rank` per cast of each spell, and per hit for "Arcane Missiles" (#394)."""
    import re

    text = cls.talent_named("Missile Barrage").rank_text[rank - 1]
    blast, missile, other = (float(x) for x in re.search(
        r"Arcane Blast spell a (\d+(?:\.\d+)?)% chance, your Arcane Missile hits a (\d+(?:\.\d+)?)% chance, "
        r"and your Arcane Wrath, Fireball, Frostbolt, and Frostfire Bolt spells a (\d+(?:\.\d+)?)% chance",
        text).groups())
    return {"Arcane Blast": blast, "Arcane Missiles": missile, "Arcane Wrath": other, "Fireball": other,
            "Frostbolt": other, "Frostfire Bolt": other}


```
2. In `rotation`, the lines
```python
    if filler.channeled:
        cast = max(cast, filler.duration)
```
   are followed by:
```python
    barrage = (missile_barrage_rule(char.cls, taken("Missile Barrage")) if taken("Missile Barrage") > 0
               else {})
    barrage_share = 0.0     # Arcane Missiles filler: the share of its casts that are barrages (#394)
    if filler.name == "Arcane Missiles" and barrage and filler.tick_period > 0:
        missiles = round(filler.duration / filler.tick_period)
        barrage_share = 1 - (1 - hit * barrage["Arcane Missiles"] / 100.0) ** missiles
        cast *= 1 - barrage_share / 2
```
3. Directly before the line `    blast = best_rank(char.spells, "Arcane Blast", char.level) if blast_stacks > 0 else None`,
   add:
```python
    if barrage.get(filler.name, 0.0) > 0:
        # a landed filler cast can proc a free, half-length Arcane Missiles: woven in when it gains (#394)
        missiles = best_rank(char.spells, "Arcane Missiles", char.level)
        if missiles is not None:
            free, missile_mods = replace(missiles, mana_cost=0), mods_for(missiles)
            if ev_of(free, missile_mods) > filler_dps * missiles.duration / 2:
                add(free, (60.0 / cast) * hit * barrage[filler.name] / 100.0, missiles.duration / 2, missile_mods)
```
4. The line
```python
    mana_per_second = cost(filler, filler_mods) / cast * (1.0 - busy / 60.0)
```
   becomes
```python
    mana_per_second = cost(filler, filler_mods) * (1 - barrage_share) / cast * (1.0 - busy / 60.0)
```

## Step 2: `src/wowforever/classes/mage.py`
In `UNMODELED`, the line `    "Missile Barrage": "proc/stack mechanic, v1",` becomes
`    "Missile Barrage": "handled in mage_rotation",`.

Nothing else changes.

## Done when
- `tests/test_missile_barrage.py` passes; no other new failures apart from mage pins.
