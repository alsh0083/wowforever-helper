"""Physical combat table (#130): expected damage of white swings, yellow attacks and ranged shots.

Classic's combat-table rules with every constant in config/physical.toml, pinned by
tests/test_physical.py. Percentages are 0-100. A white swing rolls once on a single table (miss,
dodge, glancing, crit, hit); a yellow attack first rolls whether it lands, then whether it crits.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG = Path(__file__).resolve().parents[2] / "config" / "physical.toml"
_CONFIG: dict[str, Any] | None = None


def _config() -> dict[str, Any]:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    return _CONFIG


@dataclass(frozen=True)
class Attacker:
    level: int
    attack_power: float
    crit_pct: float
    hit_pct: float


@dataclass(frozen=True)
class Target:
    level_diff: int        # target level - attacker level; anything above 3 uses the boss row
    armor: float = 0.0


def _row(target: Target) -> int:
    return min(max(target.level_diff, 0), 3)


def _effective_hit(attacker: Attacker, i: int) -> float:
    return max(0.0, attacker.hit_pct - _config()["hit_suppression"][i])


def armor_factor(attacker_level: int, armor: float) -> float:
    """Share of physical damage left after the target's armor."""
    c = _config()
    return 1 - armor / (armor + c["armor_const"] + c["armor_per_level"] * attacker_level)


def white_swing(weapon: tuple[float, float, float], attacker: Attacker, target: Target, *,
                dual_wield: bool = False, off_hand: bool = False, damage_pct: float = 0.0) -> float:
    """Expected damage of one auto-attack swing with a (min, max, speed) weapon."""
    c, i = _config(), _row(target)
    low, high, speed = weapon
    base = (((low + high) / 2 + attacker.attack_power / c["ap_per_dps"] * speed)
            * (c["off_hand_factor"] if off_hand else 1) * (1 + damage_pct / 100))
    miss = max(0.0, c["miss"][i] + (c["dual_wield_miss"] if dual_wield else 0) - _effective_hit(attacker, i))
    dodge, glance = c["dodge"][i], c["glancing"][i]
    crit = max(0.0, min(attacker.crit_pct - c["crit_suppression"][i], 100 - miss - dodge - glance))
    hit = max(0.0, 100 - miss - dodge - glance - crit)
    share = (hit + glance * c["glancing_damage"] + crit * c["crit_multiplier"]) / 100
    return base * share * armor_factor(attacker.level, target.armor)


def yellow_attack(base_damage: float, attacker: Attacker, target: Target, *,
                  crit_bonus: float = 0.0, damage_pct: float = 0.0, can_dodge: bool = True) -> float:
    """Expected damage of an ability hit: does it land, then does it crit."""
    c, i = _config(), _row(target)
    miss = max(0.0, c["miss"][i] - _effective_hit(attacker, i))
    dodge = c["dodge"][i] if can_dodge else 0.0
    landed = (100 - miss - dodge) / 100
    crit = min(100.0, max(0.0, attacker.crit_pct + crit_bonus - c["crit_suppression"][i])) / 100
    return (base_damage * (1 + damage_pct / 100) * landed * (1 + crit * (c["crit_multiplier"] - 1))
            * armor_factor(attacker.level, target.armor))


def ranged_shot(base_damage: float, attacker: Attacker, target: Target, *,
                crit_bonus: float = 0.0, damage_pct: float = 0.0) -> float:
    """A yellow attack that can't be dodged."""
    return yellow_attack(base_damage, attacker, target, crit_bonus=crit_bonus, damage_pct=damage_pct,
                         can_dodge=False)
