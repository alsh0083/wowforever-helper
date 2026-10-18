# Task #397 (part 2B): Rip in the Feral cat rotation

Make `tests/test_rip_rotation.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/classes/druid_rotation.py`. Run the test file, then the fast suite once.
  Druid regression pins (`tests/test_kit_stats.py`, opponent kits) may move; Claude re-derives them.
- Before you start, the tests in `tests/test_rip_rotation.py` fail with an ImportError. Part A already put Rip's
  `periodic_per_combo_point` into the data.

## Why
The cat ends every energy cycle with Ferocious Bite. Rip is a 12 s bleed finisher (armor doesn't reduce it) whose
damage grows per combo point. The better of two plans wins: Bite every cycle, or Rip as often as energy allows (at
most once per its duration) with Bite cycles on the energy left. Best effort (owner OK 2026-10-16).

## Step 1: add this function directly before `def cat_rotation(`
```python
def finisher_dps(energy: float, builders: float, builder_cost: float, builder_ev: float, bite_cost: float,
                 bite_ev: float, rip: tuple[float, float, float] | None = None) -> float:
    """Yellow damage per second of `builders` builders to full combo points and a finisher (#397): Ferocious Bite
    every cycle, or with `rip` = (energy cost, damage, duration) Rip as often as energy allows (at most once per
    duration) and Bite cycles on the energy left."""
    left, out = energy, 0.0
    if rip is not None:
        rip_cost, rip_damage, rip_duration = rip
        cycle = builders * builder_cost + rip_cost
        rate = min(1 / rip_duration, energy / cycle)          # Rip cycles per second
        left -= rate * cycle
        out += rate * (rip_damage + builders * builder_ev)
    return out + left / (builders * builder_cost + bite_cost) * (builders * builder_ev + bite_ev)
```

## Step 2: in `cat_rotation`
The block
```python
        n = k / cp_per_builder
        cycles = energy / (n * cost + bite.energy_cost)
        yellow = cycles * (n * builder_ev + bite_ev)
```
becomes
```python
        n = k / cp_per_builder
        yellow = finisher_dps(energy, n, cost, builder_ev, bite.energy_cost, bite_ev)
        rip = best_rank(spells, "Rip", level)
        if rip is not None and rip.duration > 0:
            # Rip at k combo points: a bleed, so it lands or not but armor and crits don't touch it (#397)
            rip_damage = ((rip.periodic_damage + rip.periodic_per_combo_point * k) * land_chance(attacker, target)
                          * (1 + (bleeding + total("damage_pct", "Rip")) / 100))
            yellow = max(yellow, finisher_dps(energy, n, cost, builder_ev, bite.energy_cost, bite_ev,
                                              rip=(rip.energy_cost, rip_damage, rip.duration)))
```
In the module docstring, `Not modeled yet: Rake's and Rip's bleeds as separate damage, Tiger's Fury, Berserk's
cleave,` becomes `Rip is kept up when it beats Ferocious Bite (#397). Not modeled yet: Rake's bleed, Tiger's Fury,
Berserk's cleave,` (reflow so lines stay under 110 characters).

Nothing else changes.

## Done when
- `tests/test_rip_rotation.py` passes; no other new failures apart from druid pins.
