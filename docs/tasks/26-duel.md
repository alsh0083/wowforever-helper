# Task #26: duel model

Implement `src/wowforever/pvp/__init__.py` (empty docstring) and `src/wowforever/pvp/duel.py` so `tests/test_duel.py` passes. Do not edit tests, `config/duel.toml` or `config/opponents/*.toml`. Read `docs/design/pvp-duel-model.md` for the why. Standard library only, type hints, short docstrings.

## Types
- `@dataclass(frozen=True) Control`: `kind` (stun | incapacitate | fear | root | slow | interrupt | silence), `duration`, `cooldown` (seconds; 0 = no cooldown).
- `@dataclass(frozen=True) Kit`: `id, role` (melee | ranged | caster), `stealth, dispels_buffs, health, dps, opener_damage, opener_stun, controls: tuple[Control, ...], removes: tuple[tuple[str, float], ...]` (what it removes, e.g. "slow,root", and its cooldown), `immunity: tuple[float, float] | None` (duration, cooldown).
- `@dataclass(frozen=True) MageSide`: `health, dps, barrier_per_min` (absorb per minute), `immunity_share` (share of time immune), `root, stun` (seconds per minute), `slow` (uptime × strength, 0-1), `interrupt` (seconds per minute).
- `@dataclass(frozen=True) DuelResult`: `score, t_mage, t_opponent, mage_uptime, opponent_uptime`.

## `load_kits(directory=config/opponents) -> list[Kit]`
Read every `*.toml` (layout: see the files): health/dps/opener from `[at_60]`, `[[controls]]`, `[[removes]]` (`removes`, `cooldown`), optional `[immunity]`. Sorted by id.

## `duel(mage, kit, variant) -> DuelResult`, variant `"mage_sees"` or `"they_open"`
Constants from `config/duel.toml` (read once).
1. **Mage uptime** = max(min_uptime, 1 − Σ(duration × 60 / cooldown) / 60) over the kit's controls with `cooldown > 0` and kind in stun, incapacitate, fear, silence, interrupt.
2. **Kiting seconds K** (per minute the opponent can't hit):
   - melee: `root + stun + slow * slow_kite_seconds`; multiplied by `removal_factor` if any `removes` entry mentions "slow" or "root" with cooldown ≤ `removal_max_cooldown`
   - ranged: `stun + root * ranged_root_share`
   - caster: `interrupt + stun`
   Opponent uptime = max(min_uptime, 1 − K / 60).
3. Opponent immunity share = duration / cooldown (0 if none). Mage DPS on them = `mage.dps * mage_uptime * (1 - that share)`; **T_mage** = kit.health / it.
4. Barrier per second = `barrier_per_min / 60`, times `dispel_barrier_factor` if the kit `dispels_buffs`.
5. Opponent DPS on the mage = `kit.dps * opponent_uptime * (1 - mage.immunity_share)`.
6. Opening damage = `opener_damage + opener_stun * kit.dps` when variant is "they_open", else 0.
7. **T_opponent** = (mage.health − opening) / (opponent DPS − barrier per second) when the denominator is positive, else `max_fight`; clamp both times to [0, max_fight].
8. score = T_opponent / (T_opponent + T_mage) (0.5 if both are 0).

## `scenario_scores(mage, kits) -> dict`
`{"wpvp_melee": ..., "wpvp_melee_they_open": ..., "wpvp_caster": ..., "stealth_ambush": ...}`; each value `{"score": mean of matchup scores, "matchups": {kit id: score}}`:
- wpvp_melee: melee kits, "mage_sees"; wpvp_melee_they_open: melee kits, "they_open"
- wpvp_caster: caster **and** ranged kits, "mage_sees"
- stealth_ambush: stealth kits, "they_open"

## `mage_side(char, filler) -> MageSide`
From `wowforever.calc.pvp_axes`: `s = survival(char, filler)`, `c = control(char, filler)`. `health = char.stats.health`; `dps` = `rotation(char, filler, target_level=char.level, assumptions=Assumptions.load(), sustained=False).dps` (from `wowforever.classes.mage_rotation`; duels are short, so no sustained buffs); `barrier_per_min = s.components["barrier"] * health`; `immunity_share = s.components["immunity"]`; root/stun/slow/interrupt from `c.components`.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
