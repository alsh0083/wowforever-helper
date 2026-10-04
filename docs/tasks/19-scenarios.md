# Task #19: v0 PvE scenarios

Implement `src/wowforever/scenarios.py` so `tests/test_scenarios.py` passes. Do not edit tests or config. Standard library only (`tomllib` for config), type hints, short docstrings.

Uses: `calc.ev` (`expected_damage`, `effective_cast_time`, `Modifiers`), `calc.talents.modifiers_for` **if it exists** (it lands in #51; until then use `Modifiers()`; import it inside a `try`), `assumptions` (`Assumptions`, `periodic_can_crit`), `stats.Stats`, `schema`.

## Types
- `@dataclass(frozen=True) Character`: `level`, `stats: Stats`, `spells: tuple[SpellRank, ...]`, `cls: ClassData`, `ranks: Mapping[int, int]` (talent id → rank)
- `@dataclass(frozen=True) QuestingParams`: `mob_hp`, `travel_seconds`, `drink_mana_per_second`, `fillers: tuple[str, ...]`
- `@dataclass(frozen=True) AoeParams`: `mob_hp`, `pack_sizes: tuple[int, ...]`, `aoe_spells`, `fillers`
- `@dataclass(frozen=True) RaidParams`: `fight_seconds`, `mana_per_second`, `fillers`, `target_level_offset: int = 3`
- `@dataclass(frozen=True) ScenarioResult`: `scenario`, `level`, `score: float`, `unit: str`, `details: dict`, `assumptions: dict` (from `Assumptions.describe()`)

## Helpers
- `scaled(spell, caster_level) -> SpellRank`: when `damage_per_level > 0`, add `damage_per_level * (min(caster_level, scaling_max_level) - spell.level)` (never negative) to both `min_damage` and `max_damage`; otherwise return `spell` unchanged.
- `best_rank(spells, name, level) -> SpellRank | None`: highest-rank spell with that name and `spell.level <= level`.
- Per-cast expected damage for a character and spell: `expected_damage(scaled(spell, level), spell_power=stats.spell_power, crit_pct=stats.crit_pct, hit_pct=stats.hit_pct, caster_level=level, target_level=…, mods=modifiers, periodic_can_crit=periodic_can_crit(spell.name, assumptions))`; cast time `effective_cast_time(spell, modifiers)`; mana cost `spell.mana_cost * (1 + mods.mana_cost_pct / 100)`.
- The **filler** is, among `fillers` available at the level, the one with the highest expected damage per second of cast time.

## Scenarios (formulas match the test comments exactly)
- `questing(char, p, assumptions)`: target = same level. `dps = ev / cast`; `time_to_kill = mob_hp / dps`; `mana_per_kill = mob_hp / ev * mana_cost`; `downtime = mana_per_kill / drink_mana_per_second`; `score = 3600 / (time_to_kill + downtime + travel_seconds)`, unit `"kills/hour"`; details `spell`, `time_to_kill`, `mana_per_kill`, `downtime`.
- `aoe_curve(char, p, assumptions)`: target = same level. AoE spell = among `aoe_spells` available, the highest expected damage per target per second (instant spells use the 1.5 s GCD via `effective_cast_time`). Per-mob AoE dps `d`. For each n: per-mob dps = `d * min(n, 4) / n` when `assumptions["aoe_target_cap"] == "soft_4"`, else `d`; `aoe_time[n] = mob_hp / per-mob dps`; `single_time[n] = n * time_to_kill` (questing filler). `break_even` = smallest n with `aoe_time[n] < single_time[n]`, else None. `score = break_even or 0`, unit `"pack size"`; details `aoe_spell`, `aoe_time`, `single_time` (dicts keyed by n), `break_even`.
- `raid(char, p, assumptions)`: target = level + `target_level_offset`. `dps = ev / cast`; `drain = mana_cost / cast - mana_per_second`; if `drain <= 0`: `time_to_oom = None`, `score = dps`; else `time_to_oom = stats.mana / drain`, `score = dps * min(1, time_to_oom / fight_seconds)`. Unit `"dps"`; details `spell`, `dps`, `time_to_oom`.

## Config
`default_params(scenario: str, level: int)` reads `config/scenarios.toml`: `"questing"` → `QuestingParams` (anchors interpolated linearly by level, clamped at the ends), `"aoe"` → `AoeParams` (mob HP from the questing anchors), `"raid"` → `RaidParams`. Fillers and AoE spells come from the top-level lists.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
