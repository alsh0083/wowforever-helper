# Task #398 (part 2): Stormstrike's +20% on the next Earth Shock

Make `tests/test_stormstrike_debuff.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit `config/shaman.toml` first, then `src/wowforever/classes/shaman_rotation.py`. Run the test
  file, then the fast suite once. Shaman regression pins (`tests/test_kit_stats.py`, opponent kits) may move;
  Claude re-derives them.
- Before you start, the tests in `tests/test_stormstrike_debuff.py` fail.

## Why
Stormstrike raises the next Lightning Bolt, Chain Lightning or Earth Shock within 12 s by 20% (its description and
SpellEffect 17364 effect 1, base points 20, build 1.60.1.70425). Enhancement casts Earth Shock on its cooldown, so
the share of shocks that follow a Stormstrike is (shock period / Stormstrike cooldown), at most 1.

## Step 1: `config/shaman.toml`
Append:
```toml
# Stormstrike: +20% damage on the next Lightning Bolt, Chain Lightning or Earth Shock within 12 s
# (description and SpellEffect 17364 effect 1, base points 20, 1.60.1.70425; #398)
stormstrike = { bonus_pct = 20.0, seconds = 12.0 }
```

## Step 2: `src/wowforever/classes/shaman_rotation.py`
1. The line
   `        spell_dps = hit * avg * (1 + spell_crit * 0.5) / max(shock.cooldown + total("cooldown", "Earth Shock"), 1.5)`
   becomes
```python
        shock_period = max(shock.cooldown + total("cooldown", "Earth Shock"), 1.5)
        spell_dps = hit * avg * (1 + spell_crit * 0.5) / shock_period
        if storm is not None and taken("Stormstrike") and storm.cooldown > 0:
            # Stormstrike's bonus on the next shock within its window: the share of shocks after one (#398)
            share = min(1.0, shock_period / storm.cooldown) if shock_period <= c["stormstrike"]["seconds"] else 0.0
            spell_dps *= 1 + c["stormstrike"]["bonus_pct"] / 100 * share
```
2. In the module docstring, `Not modeled yet: Stormstrike's Nature-damage debuff, ` becomes
   `Stormstrike's bonus on the next Earth Shock counts for the share of shocks after one (#398). Not modeled yet: `
   (reflow so lines stay under 110 characters).

Nothing else changes.

## Done when
- `tests/test_stormstrike_debuff.py` passes; no other new failures apart from shaman pins.
