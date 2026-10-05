# Task #121: diminishing returns and an energy budget for opponent controls

Make `tests/test_duel_dr.py` pass without breaking the rest of the suite. Edit `src/wowforever/pvp/duel.py`, `config/duel.toml`, `config/opponents/rogue-combat.toml` and `config/opponents/rogue-subtlety.toml`. Do not edit the tests.

## Why
Against rogues the mage's casting uptime sits at the `min_uptime` floor (0.2). The rogue's controls add up to more than 60 s per minute, because the model sums every control at its cooldown rate. Real fights have diminishing returns (DR) and are limited by the rogue's energy.

## 1. Data model (`duel.py`)
- `Control` gains `energy: float = 0.0` (energy per use), a new last field with a default.
- `Kit` gains `energy_per_minute: float = 0.0`, a new last field with a default. 0 means no energy budget.
- `load_kits` reads `energy_per_minute` from `[at_60]` (default 0) and `energy` from each `[[controls]]` entry (default 0).

## 2. Lockout (`duel()`)
Only the opponent's cast-lock seconds per minute change (`lockout`). Everything else stays as it is.

1. **Energy factor.**
   - If `kit.energy_per_minute > 0`:
     - `spend = sum(c.energy * 60 / c.cooldown for every control with cooldown > 0)`;
     - `budget = kit.energy_per_minute * max_control_energy_share`;
     - `f = min(1, budget / spend)` when `spend > 0`, else 1.
   - Otherwise `f = 1`.
2. **Per control:** `rate = c.duration * 60 / c.cooldown * f`, for controls with `cooldown > 0` whose kind is in `CAST_LOCKS`. Cooldown-0 controls stay excluded, as now.
3. **Diminishing returns.** Kinds `stun`, `incapacitate`, `disorient` and `fear` each form their own DR category.
   - Sum the rates per category.
   - Cap each category at `60 * dr_chain * d / (dr_chain * d + dr_immune_seconds)`, where `d` is the longest duration among that category's controls in this kit.
   - Kinds `interrupt` and `silence` have no DR and are summed uncapped.
4. `lockout` = the sum over all categories and the uncapped kinds. `mage_uptime = max(min_uptime, 1 - lockout / 60)`, as now.

## 3. Config
`config/duel.toml` gains, at top level, before any table:
```toml
# Diminishing returns (Classic): a chain of same-category controls lands at 100%, 50%, 25%,
# then the target is immune for 15 s. dr_chain is the chain's total in full durations.
dr_chain = 1.75
dr_immune_seconds = 15.0
# A rogue spends at most this share of its energy on controls; the rest goes to damage.
max_control_energy_share = 0.5
```

## 4. Rogue kits
In both rogue kit files, add `energy_per_minute = 600` to `[at_60]`, with the comment `# Classic energy regen 20 per 2 s`. Add `energy = ...` to each control:

| Control | energy | source comment |
|---|---|---|
| Cheap Shot | 60 | `# data` |
| Kidney Shot | 125 | `# data 25 + estimate 100 for the combo points` |
| Gouge | 45 | `# data` |
| Kick | 25 | `# data` |
| Blind | 30 | `# data` |

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_duel_dr.py` fails with a `TypeError` about unexpected keyword arguments (`energy`, `energy_per_minute`). That's the expected failure; adding the fields is the task. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Start with `src/wowforever/pvp/duel.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_duel_dr.py tests/test_duel.py`, then run the full suite once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
