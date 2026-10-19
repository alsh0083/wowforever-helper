# Task #399 (mana): Retribution tracks mana

Make `tests/test_paladin_mana.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit in this order: `src/wowforever/schema.py`, `config/melee.toml`,
  `src/wowforever/classes/paladin.py`, `src/wowforever/classes/paladin_rotation.py`. Run the test file, then the
  fast suite once. Paladin regression pins (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, opponent kits)
  may move; Claude re-derives them.
- Before you start, the tests in `tests/test_paladin_mana.py` fail.

## Why
Retribution spends mana: it recasts Seal of Command after every Judgement (judging consumes the seal), and casts
Judgement, Holy Strike and, in the execute phase, Hammer of Wrath on cooldown, plus Consecration on packs. Its mana
talents cut those costs, and Reverence keeps 30% of Spirit regen going ((15 + Spirit / 5) per 2 s tick, the
Classic paladin formula). Once out of mana it only swings white.

## Step 1: `src/wowforever/schema.py`
In `EFFECT_KINDS`, after the `"regen_while_casting",` line, add:
```python
    "seal_refund_pct",  # % of the judged seal's mana cost Judgement returns (Sanctified Judgement)
```

## Step 2: `config/melee.toml`
In the `[paladin]` section, after `uses_mana = true`, add:
```toml
# Spirit regen outside the five-second rule, per 2 s tick: regen_base + spirit / regen_spirit_div (Classic, #399)
regen_base = 15
regen_spirit_div = 5
```

## Step 3: `src/wowforever/classes/paladin.py`
1. At the end of `TALENT_EFFECTS` (after the `"Champion of the Light"` entry, before the closing `}`), add:
```python
    "Reverence": (
        EffectRule("regen_while_casting", r"Allows (\d+(?:\.\d+)?)% of your Mana regeneration to continue", ("all",)),
    ),
    "Benediction": (
        EffectRule("mana_cost_pct", r"Mana cost of all instant cast spells and abilities by (\d+(?:\.\d+)?)%",
                   ("@instant",), sign=-1),
    ),
    "Twist of Light": (
        EffectRule("mana_cost_pct", r"Mana cost of your Seal spells by (\d+(?:\.\d+)?)%", ("@seal",), sign=-1),
    ),
    "Holy Conduit": (
        EffectRule("mana_cost_pct", r"Exorcism, and Hammer of Wrath spells by (\d+(?:\.\d+)?)%",
                   ("Consecration", "Holy Wrath", "Exorcism", "Hammer of Wrath"), sign=-1),
    ),
    "Sanctified Judgement": (
        # a chance to return a share: counted at chance x share
        EffectRule("seal_refund_pct", r"(\d+(?:\.\d+)?)% chance to return (\d+(?:\.\d+)?)% of the Mana cost",
                   ("Judgement",), combine=lambda m: float(m.group(1)) * float(m.group(2)) / 100),
    ),
```
2. Delete the five `UNMODELED` lines for `"Reverence"`, `"Benediction"`, `"Holy Conduit"`,
   `"Sanctified Judgement"` and `"Twist of Light"`.
3. In `output`, the line `    return Output(r.dps, 0.0, r.dps, r.aoe)` becomes
   `    return Output(r.dps, r.mana_per_second, r.white_dps, r.aoe)`.

## Step 4: `src/wowforever/classes/paladin_rotation.py`
1. After the `CONFIG = ...` line add:
```python
MELEE = Path(__file__).resolve().parents[3] / "config" / "melee.toml"
```
2. In `class PaladinRotation`, after the `aoe` field, add:
```python
    mana_per_second: float = 0.0   # net of Reverence's regen (#399)
```
3. In `paladin_rotation`, directly after the `def total(...)` function (before `weapon = stats.main_hand`), add:
```python
    def cost(spell: SpellRank, *groups: str) -> float:
        """`spell`'s mana cost after the mana_cost_pct talents for its name, instants and `groups` (#399)."""
        cut = sum(total("mana_cost_pct", g) for g in (spell.name, "@instant", *groups))
        return spell.mana_cost * max(0.0, 1 + cut / 100)

```
4. After the line `    spell_power = stats.intellect * ...` add `    mana = 0.0`.
5. In the Seal of Command block, the seal is recast after each Judgement (Sanctified Judgement refunds part of it),
   or every `duration` seconds without Judgement. Replace
```python
        if judgement is not None:
            from wowforever.scenarios import _anchor_at
```
   with
```python
        seal = cost(best_rank(spells, "Seal of Command", stats.level), "@seal")
        if judgement is None:
            mana += seal / max(1.0, best_rank(spells, "Seal of Command", stats.level).duration)
        if judgement is not None:
            from wowforever.scenarios import _anchor_at
```
   and directly after the line `            cooldown = max(1.0, judgement.cooldown + total("cooldown", "Judgement"))` add:
```python
            mana += (seal * (1 - total("seal_refund_pct", "Judgement") / 100) + cost(judgement)) / cooldown
```
6. In the Holy Strike block, before `used.append("Holy Strike")`, add `        mana += cost(strike) / strike.cooldown`.
7. In the Hammer of Wrath block, before `used.append("Hammer of Wrath")`, add:
```python
        mana += c["hammer_of_wrath_health_pct"] / 100 * cost(hammer) / max(hammer.cooldown, 1.5)
```
8. In the Consecration block, before `used.append("Consecration")`, add `        mana += cost(consecration) / period`.
9. Replace the final `return PaladinRotation(...)` statement with:
```python
    # the share of Spirit regen that keeps going while casting (Reverence, #399)
    m = load_toml(MELEE)["paladin"]
    regen = (min(100.0, total("regen_while_casting", "all")) / 100
             * (m["regen_base"] + stats.spirit / m["regen_spirit_div"]) / 2)
    return PaladinRotation(dps=white + holy, white_dps=white, holy_dps=holy, abilities=tuple(used), aoe=aoe,
                           mana_per_second=mana - regen)
```

Nothing else changes.

## Done when
- `tests/test_paladin_mana.py` passes; no other new failures apart from paladin pins.
