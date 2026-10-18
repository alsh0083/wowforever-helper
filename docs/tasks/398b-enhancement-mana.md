# Task #398 (mana): Enhancement tracks mana

Make `tests/test_enhancement_mana.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit in this order: `config/melee.toml`, `src/wowforever/classes/shaman.py`,
  `src/wowforever/classes/shaman_rotation.py`. Run the test file, then the fast suite once. Shaman regression pins
  (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, opponent kits) may move; Claude re-derives them.
- Before you start, the tests in `tests/test_enhancement_mana.py` fail. `tests/test_class_engine.py` already
  expects Enhancement to spend mana.

## Why
Enhancement casts Earth Shock on cooldown and Stormstrike, both for mana, plus Fire Nova on packs. Improved
Stormstrike keeps part of its Spirit regen going ((15 + Spirit / 5) per 2 s tick, the Classic shaman formula).
Once dry, it swings white with Windfury; in a raid it can also skip Earth Shock, offered as an alternative Output
(the raid and dungeon scores take the best).

## Step 1: `config/melee.toml`
In the `[shaman_melee]` section, after `uses_mana = true`, add:
```toml
# Spirit regen outside the five-second rule, per 2 s tick: regen_base + spirit / regen_spirit_div (Classic, #398)
regen_base = 15
regen_spirit_div = 5
```

## Step 2: `src/wowforever/classes/shaman.py`
1. At the end of `TALENT_EFFECTS` (directly before its closing `}`), add:
```python
    "Improved Stormstrike": (
        # a chance to gain a share: counted at chance x share (#398)
        EffectRule("regen_while_casting",
                   r"(\d+(?:\.\d+)?)% chance to gain (\d+(?:\.\d+)?)% mana regeneration while casting",
                   ("@stormstrike",), combine=lambda m: float(m.group(1)) * float(m.group(2)) / 100),
    ),
```
2. Delete the `UNMODELED` line `    "Improved Stormstrike": "resource: mana regeneration after Stormstrike",`.
3. `_melee_output` becomes:
```python
def _melee_output(stats, spells, cls, ranks, target, *, pack=1):
    from wowforever.classes.shaman_rotation import enhancement_rotation
    from wowforever.melee_scenarios import Output

    r = enhancement_rotation(stats, spells, cls, ranks, target, pack=pack)
    fallback = r.white_dps + r.windfury_dps      # out of mana: swings and Windfury (#398)
    no_shock = Output(r.dps - r.shock_dps, r.mana_per_second - r.shock_mana_per_second, fallback, r.aoe)
    return Output(r.dps, r.mana_per_second, fallback, r.aoe, alternatives=(no_shock,))
```

## Step 3: `src/wowforever/classes/shaman_rotation.py`
1. In the module docstring, replace the two lines
```
Not modeled yet: Maelstrom Weapon's cheaper Lightning Bolt,
Lightning Shield orbs, totems, and mana (shocks are the main cost).
```
   with
```
Mana (#398): Earth Shock, Stormstrike and Fire Nova cost it; Improved Stormstrike keeps part of the Spirit regen.
Not modeled yet: Maelstrom Weapon's cheaper Lightning Bolt, Lightning Shield orbs (they fire when the shaman is
hit), totems.
```
2. After the `CONFIG = ...` line add:
```python
MELEE = Path(__file__).resolve().parents[3] / "config" / "melee.toml"
```
3. In `class EnhancementRotation`, after the `aoe` field, add:
```python
    windfury_dps: float = 0.0            # the Windfury part of yellow_dps (#398)
    shock_dps: float = 0.0               # the Earth Shock part of spell_dps, Stormstrike's bonus included
    mana_per_second: float = 0.0         # net of Improved Stormstrike's regen
    shock_mana_per_second: float = 0.0   # Earth Shock's part of the mana
```
4. Directly after the `def total(...)` function (before `weapon = stats.main_hand`), add:
```python
    def cost(spell: SpellRank) -> float:
        return spell.mana_cost * max(0.0, 1 + total("mana_cost_pct", spell.name) / 100)

```
5. The line `    yellow = 0.0` becomes `    yellow = windfury = mana = shock_mana = 0.0`.
6. The line `        yellow += swings * c["windfury_chance"] * extra` becomes
```python
        windfury = swings * c["windfury_chance"] * extra
        yellow += windfury
```
7. In the Stormstrike block, after the `yellow += yellow_attack(normalized, ...) / storm.cooldown` line, add
   `        mana += cost(storm) / storm.cooldown`.
8. In the Earth Shock block, after the line `            spell_dps *= 1 + c["stormstrike"]["bonus_pct"] / 100 * share`
   (still inside `if shock is not None and shock.cooldown > 0:`, at its indentation), add:
```python
        shock_mana = cost(shock) / shock_period
        mana += shock_mana
    shock_dps = spell_dps
```
   (the `shock_dps = spell_dps` line is at function level, before `nova = ...`).
9. In the Fire Nova block, after the `spell_dps += hit * avg * ...` line, add:
```python
        mana += cost(nova) / max(nova.cooldown + total("cooldown", "Fire Nova"), 1.5)
```
10. Replace the final `return EnhancementRotation(...)` statement with:
```python
    if storm is not None and taken("Stormstrike") and storm.cooldown > 0:
        # Improved Stormstrike: a share of Spirit regen keeps going while casting (#398)
        m = load_toml(MELEE)["shaman_melee"]
        mana -= (min(100.0, total("regen_while_casting", "@stormstrike")) / 100
                 * (m["regen_base"] + stats.spirit / m["regen_spirit_div"]) / 2)
    return EnhancementRotation(dps=white + yellow + spell_dps, white_dps=white, yellow_dps=yellow, spell_dps=spell_dps,
                               aoe=aoe, windfury_dps=windfury, shock_dps=shock_dps, mana_per_second=mana,
                               shock_mana_per_second=shock_mana)
```

Nothing else changes.

## Done when
- `tests/test_enhancement_mana.py` passes; no other new failures apart from shaman pins.
