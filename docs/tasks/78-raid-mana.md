# Task #78: raid mana budget from Forever numbers

Make `tests/test_raid_mana.py` pass without breaking the rest of the suite. Edit `src/wowforever/scenarios.py`, `src/wowforever/classes/mage.py`, `src/wowforever/report.py`, `config/scenarios.toml` and the one line in `tests/test_scenarios.py` named below. Do not edit `tests/test_raid_mana.py`.

## Why
The old raid model gave every build one flat budget (15 mana/s, 4500 extra mana, one 180 s fight) and scored 0 DPS after running out of mana, so mana-hungry Fire looked far worse than it plays. The numbers below come from the Forever client data (build 1.60.1.70205).

| Source | Forever data | Model |
|---|---|---|
| Evocation (spell 12051) | aura 110 +1500% mana regen, aura 134 100% regen while casting, 8 s channel, 8 min cooldown | once per fight, only when the build would otherwise run out |
| Arcane Meditation | 17/33/50% of regen continues while casting (Classic: 5/10/15%) | share of spirit regen while casting |
| Mana Ruby (spell 10058) | 1100 mana average | one-off `extra_mana` |
| Major Mana Potion (17531) | 1800 average, 2 min cooldown | consumable |
| Demonic Rune (16666) | 1200 average, 2 min cooldown, separate from potions | consumable |
| Blessing of Wisdom (25290) | 40 mana per 5 s | 8 mana/s flat `mana_per_second` |

## 1. `RaidParams` gains optional fields (defaults keep the old behaviour exactly)
```python
fight_lengths: tuple[tuple[float, float], ...] = ()   # (seconds, weight); empty -> ((fight_seconds, 1),)
consumables: tuple[tuple[float, float], ...] = ()     # (mana, cooldown seconds), uses = ceil(T / cooldown)
spirit_regen: bool = False      # add spirit regen while casting (Arcane Meditation share) and allow Evocation's value
evocation: bool = False
evocation_seconds: float = 8.0
evocation_regen_pct: float = 1500.0
fallback: bool = False          # after OOM keep casting at the mana-limited rate instead of 0 DPS
```

## 2. Helpers in `scenarios.py`
- `spirit_regen(stats) -> float`: mana per second outside the five-second rule, Classic mage formula `(13 + spirit / 4) / 2`.
- `combat_regen(char, p) -> float`: `p.mana_per_second`, plus `spirit_regen(char.stats) * share / 100` when `p.spirit_regen`, where `share` is the character's Arcane Meditation `regen_while_casting` value (0 when untaken).

Add the talent rule in `classes/mage.py`: `"Arcane Meditation": (EffectRule("regen_while_casting", r"Allows (\d+(?:\.\d+)?)% of your Mana regeneration", ("all",)),)` and remove it from `UNMODELED`.

## 3. `raid()` per fight length T
With the rotation `dps` and `mps` (mana per second) as now, `i = combat_regen(char, p)`, `d = mps - i`:
- If `d <= 0`: score_T = dps, no Evocation.
- Else budget `B = mana + extra_mana + sum(mana * ceil(T / cd) for consumables)`. If `p.evocation` and `B / d < T`: Evocation is used, `B += spirit_regen(stats) * (1 + evocation_regen_pct / 100) * evocation_seconds` and the active casting time is `A = T - evocation_seconds`; otherwise `A = T`.
- `t_full = min(A, B / d)`. After that the mage casts at the fallback rate `f` for `A - t_full` seconds: `f = 0` unless `p.fallback`; with fallback, `f = max(rot.dps * min(1, i / rot.mps))` over the sustained rotations of every rank of the chosen filler learned by this level plus the best rank of each other filler (this is how Fire downranks or swaps to Frostbolt when dry).
- `score_T = (dps * t_full + f * (A - t_full)) / T`.

`score` = weighted mean of `score_T`. `details`: `spell`, `dps` (raw), `time_to_oom` (at `p.fight_seconds`: `B / d` plus `evocation_seconds` if Evocation was used, `None` if never OOM), `evocation_used` (at `fight_seconds`), `fallback_spell` (`"<name> rank <n>"` of the best fallback, or `None`), `by_length` (`{T: score_T}`).

## 4. Config
`[raid]`: `fight_seconds = 180`, `fight_lengths = [[90, 1], [180, 2], [300, 1]]`, `mana_per_second = 8` (Blessing of Wisdom; gear MP5 is not tracked yet), `extra_mana = 1100` (Mana Ruby), `consumables = [[1800, 120], [1200, 120]]`, `spirit_regen = true`, `evocation = true`, `fallback = true`, comment each with the source row above. `[dungeon]`: `fight_seconds = 60`, `mana_per_second = 0`, `extra_mana = 0`, `spirit_regen = true`, `fallback = true`, no consumables or Evocation (drink between pulls). `default_params` reads all of them (TOML lists become tuples of tuples). In `tests/test_scenarios.py::test_default_params_from_config_scale_with_level` the last line stays as is (fight_seconds is still 180).

## 5. Report
`report.py` raid entry gains `"raw_dps": round(r.details["dps"], 1)` and `"fallback_spell": r.details["fallback_spell"]`.

## Done when
`.venv/Scripts/python -m pytest` passes in full.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_raid_mana.py` fails with `ImportError: cannot import name 'combat_regen'`: that is the expected failure, because implementing those names is the task. Install nothing and request no elevation. Start by editing `src/wowforever/scenarios.py`; iterate with `.venv/Scripts/python -m pytest tests/test_raid_mana.py tests/test_scenarios.py`, then run the full suite once at the end.
