# Task #130: physical combat table

Make `tests/test_physical.py` pass without breaking the rest of the suite. Create `src/wowforever/physical.py`. `config/physical.toml` is written already. Do not edit the tests or config.

## Why
Rogue and hunter damage (#131, #132) needs the expected damage of white swings, yellow attacks and ranged shots against a target some levels up. These are Classic's combat-table rules. Every constant is in `config/physical.toml`, so in-game checks can replace them later.

## API (`src/wowforever/physical.py`)
```python
@dataclass(frozen=True)
class Attacker:
    level: int
    attack_power: float
    crit_pct: float
    hit_pct: float

@dataclass(frozen=True)
class Target:
    level_diff: int        # target level - attacker level; 0..3, anything above 3 uses index 3
    armor: float = 0.0

def armor_factor(attacker_level: int, armor: float) -> float
def white_swing(weapon: tuple[float, float, float], attacker: Attacker, target: Target, *,
                dual_wield: bool = False, off_hand: bool = False, damage_pct: float = 0.0) -> float
def yellow_attack(base_damage: float, attacker: Attacker, target: Target, *,
                  crit_bonus: float = 0.0, damage_pct: float = 0.0, can_dodge: bool = True) -> float
def ranged_shot(base_damage: float, attacker: Attacker, target: Target, *,
                crit_bonus: float = 0.0, damage_pct: float = 0.0) -> float
```
Read the config once with `tomllib`, from the repo-root `config/physical.toml`, the way `pvp/duel.py` reads `config/duel.toml`. Let `i = min(max(target.level_diff, 0), 3)`. All percentages are 0–100.

- `armor_factor = 1 - armor / (armor + armor_const + armor_per_level * attacker_level)`, which is 1.0 when armor is 0.
- **Effective hit:** `eff_hit = max(0, hit_pct - hit_suppression[i])`.
- **`white_swing`** (one roll on a single table):
  - `base = ((min + max) / 2 + attack_power / ap_per_dps * speed) * (off_hand_factor if off_hand else 1) * (1 + damage_pct / 100)`.
  - `miss = max(0, miss[i] + (dual_wield_miss if dual_wield else 0) - eff_hit)`.
  - `dodge = dodge[i]`, `glance = glancing[i]`.
  - `crit = max(0, min(crit_pct - crit_suppression[i], 100 - miss - dodge - glance))`.
  - `hit = max(0, 100 - miss - dodge - glance - crit)`.
  - Result: `base * (hit + glance * glancing_damage + crit * crit_multiplier) / 100 * armor_factor(attacker.level, target.armor)`.
- **`yellow_attack`** (two rolls: does it land, then does it crit):
  - `miss = max(0, miss[i] - eff_hit)`; `dodge = dodge[i] if can_dodge else 0`; `landed = (100 - miss - dodge) / 100`.
  - `crit = min(100, max(0, crit_pct + crit_bonus - crit_suppression[i])) / 100`.
  - Result: `base_damage * (1 + damage_pct / 100) * landed * (1 + crit * (crit_multiplier - 1)) * armor_factor(...)`.
- **`ranged_shot`** is `yellow_attack(..., can_dodge=False)`.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_physical.py` fails with `ModuleNotFoundError: No module named 'wowforever.physical'`. That's the expected failure. Install nothing and ask for no elevation. Write the file with `tools/apply_patch.py` (see AGENTS.md). Iterate with `.venv/Scripts/python -m pytest tests/test_physical.py`, then run the full suite once at the end. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
