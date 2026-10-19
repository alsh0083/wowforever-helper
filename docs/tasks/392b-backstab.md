# Task #392 (Backstab): a dagger and Backstab when that scores higher

Make `tests/test_backstab.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit in this order: `config/rogue.toml`, `src/wowforever/weapon_talents.py`,
  `src/wowforever/classes/rogue_rotation.py`, `src/wowforever/classes/rogue.py`. Run the test file, then the fast
  suite once. Rogue regression pins (`tests/test_dungeon_mana.py`, `tests/test_kit_stats.py`, opponent kits) may
  move; Claude re-derives them.
- Before you start, the tests in `tests/test_backstab.py` fail.

## Why
Backstab is the Assassination and Subtlety builder, but it needs a dagger in the main hand. The stat rows carry no
weapon type, so a dagger is modeled as the main hand's weapon DPS at a dagger's speed (1.8 s), and the rogue takes
whichever of that and its usual weapon scores higher (owner: the best weapon for each scenario, #386). Puncturing
Wounds' 45% chance of an extra combo point counts on every landed Backstab.

## Step 1: `config/rogue.toml`
After the `normalized_speed = ...` line, add:
```toml
# Backstab needs a dagger (#392): the main hand's weapon DPS at this speed (a typical dagger's)
dagger_speed = 1.8
```

## Step 2: `src/wowforever/weapon_talents.py`
1. `best_weapon` gains a keyword-only parameter: its signature becomes
```python
def best_weapon(run: Callable[[Any, Target], Any], stats: Any, target: Target, cls: ClassData,
                ranks: Mapping[int, int], *, only: str | None = None) -> tuple[Any, str | None]:
```
2. Add to its docstring, after the first sentence: ` With `only`, just that weapon's branch.`
3. The loop line `    for weapon, kind in BRANCHES[name].items():` is followed by:
```python
        if only is not None and weapon != only:
            continue
```

## Step 3: `src/wowforever/classes/rogue_rotation.py`
1. In the module docstring, replace `Not modeled yet: Backstab (#392).` with
   `Backstab (#392): the builder when the caller passes backstab=True with a dagger row.`
2. `rogue_rotation`'s signature gains `backstab: bool = False` after `pack: int = 1`:
```python
def rogue_rotation(stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                   ranks: Mapping[int, int], target: Target, *, pack: int = 1,
                   backstab: bool = False) -> RogueRotation:
```
3. In the builder choice, before the final `    else:` (the Sinister Strike branch), add:
```python
    elif backstab and learned("Backstab") is not None:
        builder, speed = learned("Backstab"), c["normalized_speed"]["dagger"]
```
4. Directly after the line
   `    cp = builder.combo_points * land + land * crit_use * total("proc_chance", "@builder_crit") / 100`
   add:
```python
    if builder.name == "Backstab":
        cp += land * total("proc_chance", "@backstab_combo") / 100   # Puncturing Wounds (#392)
```

## Step 4: `src/wowforever/classes/rogue.py`
1. Add these two lines at the top, after the `from wowforever.classes import ...` line (keep one blank line
   between them and the import, and two blank lines before the `# Trait tree 1111` comment):
```python
from dataclasses import replace
from pathlib import Path
```
2. Directly before the line `# --- class engine (#309): this module is the rogue's ClassEngine ---...` add:
```python
CONFIG = Path(__file__).resolve().parents[3] / "config" / "rogue.toml"


def dagger(stats):
    """`stats` with a dagger in the main hand (#392): the same weapon DPS at config/rogue.toml's `dagger_speed`."""
    from wowforever.toml_cache import load_toml

    mn, mx, speed = stats.main_hand
    f = load_toml(CONFIG)["dagger_speed"] / speed
    return replace(stats, main_hand=(mn * f, mx * f, speed * f))


```
3. `output` becomes:
```python
def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None, sustained=False):
    from wowforever.classes.rogue_rotation import rogue_rotation
    from wowforever.melee_scenarios import Output
    from wowforever.scenarios import best_rank
    from wowforever.weapon_talents import best_weapon

    # the usual weapon, or a dagger and Backstab: whichever scores higher (#386, #392)
    r, _ = best_weapon(lambda s, t: rogue_rotation(s, spells, cls, ranks, t, pack=pack),
                       stats, target, cls, ranks)
    if stats.main_hand is not None and best_rank(spells, "Backstab", stats.level) is not None:
        stab, _ = best_weapon(lambda s, t: rogue_rotation(s, spells, cls, ranks, t, pack=pack, backstab=True),
                              dagger(stats), target, cls, ranks, only="dagger")
        r = max(r, stab, key=lambda x: x.dps)
    return Output(r.dps, 0.0, r.dps, r.aoe)
```

Nothing else changes.

## Done when
- `tests/test_backstab.py` passes; no other new failures apart from rogue pins. Before you start,
  `tests/test_class_engine.py` also fails for the rogue (it already expects the dagger run); it passes after Step 4.
