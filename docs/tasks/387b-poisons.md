# Task #387 (part 2): poison damage in the rogue rotation

Make `tests/test_poisons.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order; create `src/wowforever/classes/poisons.py` first. Run the test file after
  step 3, then once more at the end, then the fast suite once. Rogue regression pins (`tests/test_dungeon_mana.py`,
  `tests/test_kit_stats.py`, opponent kits, `tests/test_class_engine.py` totals) may move; Claude re-derives them.
- Before you start, every test in `tests/test_poisons.py` fails with an ImportError. Part 1 already put the poison
  ranks into the dataset.

## Why
Poisons are about 10-15% of a rogue's damage and the model counts none of it. Each landed hit of a poisoned weapon
applies the poison with a chance. Forever's proc chances aren't in the cached client tables; owner (2026-10-17):
use a researched assumption for now, Classic's 20% (Instant) and 30% (Deadly), 5 Deadly stacks.

## Step 1: create `src/wowforever/classes/poisons.py` with exactly this content
```python
"""Rogue poisons (#387): damage per landed weapon hit, and the best poison on each weapon.

Each landed hit of a poisoned weapon applies its poison with the poison's chance (config/rogue.toml; Improved
Poisons adds to it). A poison is a Nature spell, so it lands on the spell hit table. Instant Poison deals its
damage at once and can crit (x1.5 at the rogue's crit, Malice included); Deadly Poison stacks up to
`max_stacks`, each stack dealing its periodic damage over its duration, and both weapons' applications feed
one stack. Vile Poisons raises both.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence

from wowforever.schema import SpellRank

SPELL_CRIT_MULTIPLIER = 1.5


def poison_dps(poison: SpellRank, hits_per_second: float, *, chance_pct: float, land: float, crit: float,
               damage_pct: float, max_stacks: int) -> float:
    """Damage per second of `poison` on a weapon landing `hits_per_second`."""
    applied = hits_per_second * chance_pct / 100 * land
    if poison.periodic_damage > 0 and poison.duration > 0:
        stacks = min(max_stacks, applied * poison.duration)
        return stacks * poison.periodic_damage / poison.duration * (1 + damage_pct / 100)
    average = (poison.min_damage + poison.max_damage) / 2
    return applied * average * (1 + crit * (SPELL_CRIT_MULTIPLIER - 1)) * (1 + damage_pct / 100)


def best_poisons(poisons: Sequence[SpellRank], hits: Sequence[float], *, chance_pct: Mapping[str, float],
                 land: float, crit: float, damage_pct: float, max_stacks: int) -> tuple[float, tuple[str, ...]]:
    """(damage per second, poison name per weapon) of the best poison on each weapon, where `hits` holds each
    weapon's landed hits per second (main hand, then off hand); (0.0, ()) with no poison learned."""
    best: tuple[float, tuple[str, ...]] = (0.0, ())
    for combo in itertools.product(poisons, repeat=len(hits)):
        dps = 0.0
        for poison in {p.name: p for p in combo}.values():
            on = sum(h for h, p in zip(hits, combo) if p.name == poison.name)
            dps += poison_dps(poison, on, chance_pct=chance_pct[poison.name], land=land, crit=crit,
                              damage_pct=damage_pct, max_stacks=max_stacks)
        if dps > best[0]:
            best = (dps, tuple(p.name for p in combo))
    return best
```

## Step 2: `src/wowforever/physical.py`
Directly after the whole `land_chance` function (before `def yellow_crit_chance`), add:
```python
def white_land_chance(attacker: Attacker, target: Target, *, dual_wield: bool = False,
                      dodge_reduction: float = 0.0) -> float:
    """Probability (0-1) that an auto-attack swing connects (hits, glances or crits)."""
    c, i = _config(), _row(target)
    miss = max(0.0, c["miss"][i] + (c["dual_wield_miss"] if dual_wield else 0) - _effective_hit(attacker, i))
    dodge = max(0.0, c["dodge"][i] - dodge_reduction)
    return (100 - miss - dodge) / 100
```
Keep two blank lines between top-level functions.

## Step 3: `config/rogue.toml` and `src/wowforever/classes/rogue.py`
1. Append to `config/rogue.toml`:
   ```toml
   # Poisons (#387): chance per landed hit to apply each poison, and Deadly Poison's stack cap. Classic 1.12 values
   # (Instant 20%, Deadly 30%, 5 stacks): Forever's proc chances (SpellAuraOptions) aren't in the cached tables.
   # Assumption chosen 2026-10-17 at the owner's request; confidence LOW until checked in Forever.
   poisons = { instant_chance_pct = 20.0, deadly_chance_pct = 30.0, deadly_max_stacks = 5 }
   ```
2. In `rogue.py` `TALENT_EFFECTS`, directly after the `"Vile Poisons": (...),` entry, add:
   ```python
       "Improved Poisons": (
           EffectRule("proc_chance", r"chance to apply Poisons to your target by (\d+(?:\.\d+)?)%",
                      ("@poison",)),
       ),
   ```
3. In `UNMODELED`, delete the line `    "Improved Poisons": "poison: better apply chance, charge savings",`.

## Step 4: `src/wowforever/classes/rogue_rotation.py`
1. Module docstring: the line
   `Not modeled yet: poisons, Backstab (needs the main-hand weapon type) and Hack and Slash extra attacks.`
   becomes
   `Poisons (#387): classes/poisons.py, on every landed hit. Not modeled yet: Backstab (#392).`
2. Imports: add `from wowforever.calc.ev import miss_chance` and `from wowforever.classes.poisons import best_poisons`
   above `from wowforever.melee_stats import MeleeStats`, and add `white_land_chance` to the `wowforever.physical`
   import list.
3. In `class RogueRotation`, after the `aoe` field add:
   ```python
       poisons: tuple[str, ...] = ()   # the poison on each weapon (main hand, then off hand), #387
       poison_dps: float = 0.0
   ```
4. In `rogue_rotation`, directly before the line `    aoe: tuple[str, ...] = ()`, add:
   ```python
       # poisons (#387): every landed hit of a poisoned weapon can apply its poison
       p = c["poisons"]
       white_land = white_land_chance(attacker, target, dual_wield=dual, dodge_reduction=dr)
       hits = [haste / stats.main_hand[2] * white_land + cycles * land * (n + finish_share)]
       if dual:
           hits.append(haste / stats.off_hand[2] * white_land
                       + (cycles * land * n if builder.weapon_hits >= 2 else 0.0))
       chance = total("proc_chance", "@poison")
       known = tuple(s for s in map(learned, ("Instant Poison", "Deadly Poison")) if s is not None)
       poison_dps, poisons = best_poisons(
           known, tuple(hits),
           chance_pct={"Instant Poison": p["instant_chance_pct"] + chance,
                    "Deadly Poison": p["deadly_chance_pct"] + chance},
           land=1 - miss_chance(level, level + target.level_diff, 0.0) / 100,
           crit=yellow_crit_chance(attacker, target), damage_pct=total("damage_pct", "@poison"),
           max_stacks=p["deadly_max_stacks"])
       yellow += poison_dps
   ```
5. The final `return RogueRotation(...)` gains `poisons=poisons, poison_dps=poison_dps` after `aoe=aoe`.

## Step 5: `src/wowforever/report.py`
In `MELEE_CAVEAT`, `"rules; poisons, Backstab, Hack and Slash and hunter pet details aren't modeled yet, and "`
becomes `"rules; rogue poisons use Classic proc chances, Backstab and hunter pet details aren't modeled yet, and "`.

Nothing else changes.

## Done when
- `tests/test_poisons.py` passes (7 tests); no other new failures apart from rogue pins.
