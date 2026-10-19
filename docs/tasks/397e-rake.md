# Task #397 (part 4): Rake in the cat rotation

Make `tests/test_rake.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/druid_rotation.py`. Run the test file, then the fast suite once.
  Druid regression pins (`tests/test_kit_stats.py`, opponent kits) may move; Claude re-derives them.
- Before you start, the tests in `tests/test_rake.py` fail with an ImportError.

## Why
Rake (40 Energy: a hit plus a 9 s bleed, 1 combo point) isn't in the cat rotation. Best effort (owner OK
2026-10-16): once per its duration it takes a builder's place. It gives the same combo point, so the cycle keeps its
shape; the damage changes by (Rake - builder) and the Energy it saves is worth the cycle's yellow damage per Energy.
It's only taken when that gain is positive. The bleed lands or not; armor doesn't reduce it.

## Step 1: add this function directly before `def cat_rotation(`
```python
def rake_gain(rake_damage: float, builder_ev: float, builder_cost: float, rake_cost: float,
              damage_per_energy: float, duration: float) -> float:
    """Extra damage per second from Rake taking a builder's place once per its duration (#397), or 0 if it loses."""
    gain = (rake_damage - builder_ev + (builder_cost - rake_cost) * damage_per_energy) / duration
    return max(0.0, gain)
```

## Step 2: in `cat_rotation`
Directly before the line `    return CatRotation(dps=white + yellow, white_dps=white, yellow_dps=yellow, builder=builder.name)`
add:
```python
    rake = best_rank(spells, "Rake", level)
    if rake is not None and rake.duration > 0 and yellow > 0 and energy > 0:
        # Rake in a builder's place once per its duration (#397): its hit and its bleed (armor-free)
        pct = bleeding + total("damage_pct", "Rake")
        rake_damage = (yellow_attack((rake.min_damage + rake.max_damage) / 2, attacker, target, damage_pct=pct,
                                     crit_damage_pct=crit_damage)
                       + rake.periodic_damage * land_chance(attacker, target) * (1 + pct / 100))
        rake_cost = max(0.0, rake.energy_cost + total("energy_cost", "Rake"))
        yellow += rake_gain(rake_damage, builder_ev, cost, rake_cost, yellow / energy, rake.duration)
```
In the module docstring, `Not modeled yet: Rake's bleed, Tiger's Fury,` becomes
`Rake takes a builder's place once per its duration when it gains (#397). Not modeled yet: Tiger's Fury,`
(keep lines under 110 characters).

Nothing else changes.

## Done when
- `tests/test_rake.py` passes; no other new failures apart from druid pins.
