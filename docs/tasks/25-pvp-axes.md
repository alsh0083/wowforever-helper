# Task #25: survival and control scoring

Make `tests/test_pvp_axes.py` pass. Do not edit tests or `config/pvp_axes.toml`. Standard library only (`tomllib`), type hints, short docstrings.

## 1. Talent effect rules (`src/wowforever/classes/mage.py`)
Move these talents from `UNMODELED` into `TALENT_EFFECTS` (numbers parsed from each rank's text, like the existing rules):
| Talent | kind | applies_to | pattern captures |
|---|---|---|---|
| Permafrost | `duration` | `("@chill",)` | the % in "duration of your Chill effects by N%" |
| Permafrost | `slow_pct` | `("@chill",)` | the % in "speed by an additional N%" |
| Improved Frost Nova | `cooldown` (sign −1) | `("Frost Nova",)` | "by N sec" |
| Frostbite | `proc_chance` | `("@chill",)` | "a N% chance to Freeze" |
| Improved Counterspell | `control` | `("Counterspell",)` | "Silences the target for N sec" |
Impact (`proc_chance`, fire) and Burning Soul (`pushback_pct`, fire) are already modeled.

## 2. `src/wowforever/calc/pvp_axes.py`
- `@dataclass(frozen=True) AxisScore`: `score: float`, `components: dict[str, float]` (raw values, before shares).
- `survival(char: Character, filler: SpellRank) -> AxisScore` and `control(char: Character, filler: SpellRank) -> AxisScore`.
- Score = Σ `weight * min(1, component / reference)` over the axis' components in the config. Read the config once (module-level cache is fine).

Helpers: `talent_rank(char, name)` = rank in `char.ranks` (0 if absent); `effect_value(char, talent, kind)` = that effect's value at the taken rank (0 if not taken). `best_rank(char.spells, name, char.level)` (from `wowforever.scenarios`) = learned spell. **Ice Barrier, Ice Block and Cold Snap come from talents**: they count only when the talent is taken *and* the spell is learned by the level.

Filler cycle: `cast = effective_cast_time(filler, modifiers_for(filler, char.cls, char.ranks))` (both already exist). The filler **chills** when `filler.slow_pct > 0`; it's a **fire hit** when `"fire" in filler.schools`.

### Survival components
- `barrier` = Ice Barrier absorb × 60 / its cooldown / `char.stats.health`
- `immunity` = Ice Block duration × uses / 600, uses = 600 / Ice Block cooldown + (1 if Cold Snap is available)
- `pushback` = min(1, (Burning Soul pushback_pct / 100 if the filler is a fire hit else 0) + (`barrier_pushback_share` if Ice Barrier is available else 0))
- `escapes` = 60 / Blink cooldown + 60 / (Frost Nova cooldown + Improved Frost Nova's (negative) cooldown value), counting each only if learned

### Control components
- `slow` = (min(1, filler.duration × (1 + Permafrost duration% / 100) / cast) × (filler.slow_pct + Permafrost slow%) / 100) if the filler chills, else 0
- `root` = Frost Nova root × 60 / its reduced cooldown (if learned) + (Frostbite proc% / 100 × 60 / cast × 5 if the filler chills)
- `stun` = Impact proc% / 100 × 60 / cast × 2 if the filler is a fire hit, else 0
- `interrupt` = (Counterspell interrupt_lockout + Improved Counterspell silence seconds) × 60 / Counterspell cooldown, if learned

The 5 s freeze and 2 s stun come from the talent text; reading them from the text is a bonus, constants with a comment are fine.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
