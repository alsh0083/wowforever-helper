# Task #396/#398: Soul Siphon and Elemental Devastation

Make `tests/test_siphon_devastation.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Do the steps in order; run the test file at the end, then the fast suite once. Warlock and shaman
  regression pins (`tests/test_kit_stats.py`, opponent kits, `tests/test_dungeon_mana.py`) may move; Claude
  re-derives them.
- Before you start, the tests in `tests/test_siphon_devastation.py` fail.

## Why
Soul Siphon: drains deal 12% more per other Affliction effect on the target, up to 36%. The caster rotation passes
`dot:<name>` conditions for the DoTs it keeps up, so three copies of the rule, one per Affliction DoT, count each
DoT that's up (and cap at 36% by themselves). Elemental Devastation: an Earth Shock crit gives +9% melee crit for
10 s; best effort (owner OK 2026-10-16), its uptime is 1 - (1 - spell crit)^(Earth Shocks per 10 s).

## Step 1: `src/wowforever/classes/warlock.py`
Add to `TALENT_EFFECTS`:
```python
    # one rule per Affliction DoT, each counting while that DoT is up (#396)
    "Soul Siphon": tuple(
        EffectRule("damage_pct", r"Wrack spells by (\d+(?:\.\d+)?)% per each of your other Affliction effects",
                   ("Drain Life", "Drain Soul", "Wrack", f"@dot:{dot}"))
        for dot in ("Corruption", "Bane of Agony", "Siphon Life")),
```
and delete the `UNMODELED` line `    "Soul Siphon": "damage: drains scale with afflictions",`.

## Step 2: `src/wowforever/classes/shaman.py`
Add to `TALENT_EFFECTS`:
```python
    "Elemental Devastation": (
        EffectRule("crit_chance", r"chance to get a Critical Strike with melee attacks by (\d+(?:\.\d+)?)%",
                   ("@devastation",)),
        EffectRule("duration", r"melee attacks by \d+(?:\.\d+)?% for (\d+(?:\.\d+)?) sec", ("@devastation",)),
    ),
```
and delete the `UNMODELED` line `    "Elemental Devastation": "proc: spell crits raise melee crit",`.

## Step 3: `src/wowforever/classes/shaman_rotation.py`, `enhancement_rotation`
The line
`    attacker = Attacker(level, ap, stats.crit_pct + total("crit_chance", "all"), stats.hit_pct + total("hit_chance", "all"))`
becomes
```python
    melee_crit = stats.crit_pct + total("crit_chance", "all")
    shock = best_rank(spells, "Earth Shock", level)
    if shock is not None and shock.cooldown > 0 and total("duration", "@devastation") > 0:
        # Earth Shock crits raise melee crit for a while (Elemental Devastation, #398): its average uptime
        shocks = total("duration", "@devastation") / max(shock.cooldown + total("cooldown", "Earth Shock"), 1.5)
        uptime = 1 - (1 - min(1.0, (stats.crit_pct + total("crit_chance", "all")) / 100)) ** shocks
        melee_crit += total("crit_chance", "@devastation") * uptime
    attacker = Attacker(level, ap, melee_crit, stats.hit_pct + total("hit_chance", "all"))
```
The later line `    shock = best_rank(spells, "Earth Shock", level)` (before the Earth Shock damage block) stays as it is.

Nothing else changes.

## Done when
- `tests/test_siphon_devastation.py` passes; no other new failures apart from warlock and shaman pins.
