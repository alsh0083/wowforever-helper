# Task #384/#395/#392: bonuses while a DoT is up, Devouring Contagion, Flawless Execution

Make `tests/test_dot_bonuses.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `src/wowforever/caster.py` first, then the class modules, then `rogue_rotation.py`. Run the
  test file at the end, then the fast suite once. Priest, shaman and rogue regression pins
  (`tests/test_dungeon_mana.py`, `tests/test_dot_mana.py`'s dungeon values, `tests/test_kit_stats.py`, opponent
  kits) may move; Claude re-derives them.
- Before you start, most tests in `tests/test_dot_bonuses.py` fail.

## Why
Some damage depends on a DoT being up: Power in Light (Smite +10% on Shadow Word: Pain targets) and Lava Burst's
own +20% with Flame Shock (SpellEffect 408490 effect 1, base points 20, build 1.60.1.70425). The caster rotation
keeps its DoTs up, so spells cast after them can count on it. `modifiers_for` already takes `conditions`
(`@`-tokens); the rotation passes `dot:<name>` for each DoT it keeps up.

## Step 1: `src/wowforever/caster.py`
1. `cast` becomes:
```python
def cast(spell: SpellRank, stats: Stats, cls: ClassData, ranks: Mapping[int, int], target_level: int,
         assumptions: Assumptions, conditions: frozenset[str] = frozenset(),
         extra_damage_pct: float = 0.0) -> tuple[float, float, float]:
    """(expected damage, seconds of casting, mana) for one cast; instants take a global cooldown and
    channels their full duration. `conditions` switch on `@`-token talent rules (`dot:<name>` while that DoT is
    up) and `extra_damage_pct` adds a spell's own bonus (Lava Burst with Flame Shock, #384)."""
    mods = modifiers_for(spell, cls, ranks, conditions)
    if extra_damage_pct:
        mods = replace(mods, damage_pct=mods.damage_pct + extra_damage_pct)
```
   The rest of the function body (from `    ev = expected_damage(` on) stays as it is.
2. In `caster_rotation`, directly before the line `    for kind in ("dots", "cooldowns"):` add:
```python
    def boosts(name: str) -> tuple[frozenset[str], float]:
        """Conditions and extra damage % for `name` from the DoTs already kept up (#384, #395)."""
        up = frozenset(f"dot:{n}" for n in used if n in plan.get("dots", ()))
        dot, pct = plan.get("dot_bonus", {}).get(name, (None, 0.0))
        return up, (pct if f"dot:{dot}" in up else 0.0)
```
3. In that loop, the line `            ev, seconds, cost = cast(spell, stats, cls, ranks, target_level, assumptions)`
   becomes
```python
            conditions, extra = boosts(name)
            ev, seconds, cost = cast(spell, stats, cls, ranks, target_level, assumptions, conditions, extra)
```
4. In the filler loop, the line `        ev, seconds, cost = cast(spell, stats, cls, ranks, target_level, assumptions)`
   becomes
```python
        conditions, extra = boosts(name)
        ev, seconds, cost = cast(spell, stats, cls, ranks, target_level, assumptions, conditions, extra)
```

## Step 2: class modules
1. `src/wowforever/classes/shaman.py`, `ROTATION`: after the `"fillers"` line add
```python
    # Lava Burst's own effect 1 (SpellEffect 408490, 1.60.1.70425): +20% damage with Flame Shock up (#384)
    "dot_bonus": {"Lava Burst": ("Flame Shock", 20.0)},
```
2. `src/wowforever/classes/priest.py`, `TALENT_EFFECTS`: add
```python
    "Power in Light": (
        EffectRule("damage_pct", r"Smite and Penance spells deal (\d+(?:\.\d+)?)% increased damage",
                   ("Smite", "Penance", "@dot:Shadow Word: Pain")),
    ),
    "Devouring Contagion": (
        EffectRule("mana_cost_pct", r"mana cost of your Devouring Plague by (\d+(?:\.\d+)?)%",
                   ("Devouring Plague",), sign=-1),
    ),
```
   and delete the two `UNMODELED` lines for `"Power in Light"` and `"Devouring Contagion"`.
3. `src/wowforever/classes/rogue.py`, `TALENT_EFFECTS`: add
```python
    "Flawless Execution": (
        EffectRule("energy_cost", r"Energy cost of your Eviscerate ability by (\d+(?:\.\d+)?)",
                   ("Eviscerate",), sign=-1),
    ),
```
   and delete the `UNMODELED` line `    "Flawless Execution": "resource: cheaper Eviscerate",`.

## Step 3: `src/wowforever/classes/rogue_rotation.py`
The line `    cycles = energy / (n * cost + evis.energy_cost - refund)` becomes
`    cycles = energy / (n * cost + evis.energy_cost + total("energy_cost", "Eviscerate") - refund)`

Nothing else changes.

## Done when
- `tests/test_dot_bonuses.py` passes (9 tests); no other new failures apart from priest, shaman and rogue pins.
