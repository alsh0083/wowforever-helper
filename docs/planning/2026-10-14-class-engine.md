# Class engine: each class module runs its own rotation (planning, 2026-10-14)

From the 2026-10-14 architecture review, candidate 1 (owner picked it). It's a refactor, so scores don't change: every slice must regenerate the reports with no diff.

## The friction

The class registry (`classes/__init__.py`) maps a name to a module path, and a class module's other "interface" is a set of loose constants (`ENGINE`, `MELEE_TREES`, `HYBRIDS`, `ROTATION`, …) read through `getattr` with defaults. Nothing on a class module says "run my rotation". Instead, five modules each decide with their own `if class_name ==` chain:

| Where | What it dispatches |
|---|---|
| `melee_scenarios.rotation_output` (137-186) | the rotation, and how each result becomes an `Output` |
| `melee_scenarios.aoe` (246-248), `questing` (198) | caster AoE vs pack rotation; the hunter pet tanks |
| `describe.rotation_facts` (188-250) | the same rotations again, for the build description |
| `group.dungeon_dps` (294-301), `player_kind` (376), `_kind_for` (455) | the hybrid row, hunter = ranged |
| `pvp/class_pvp.class_side` (169-175) | re-runs the hunter rotation just to read its mode |
| `report.py` (527, 537) | the hybrid check, inline again |

All seven AoE-pull slices (#260-#304) had to edit `melee_scenarios.py`. The hybrid check ("a druid/shaman build with most points in a melee tree fights with the melee stat row") is written out 8-10 times, and `_has_pet` is reached across three modules.

## Decisions

- **Interface: a `ClassEngine` protocol, implemented by each scored class module.** `classes.engine(name)` returns the class module as a `ClassEngine`. It raises `ValueError` for a class without one (mage and unscored classes). The module is the adapter: eight classes, eight adapters, so the seam is real.

  | Member | Replaces |
  |---|---|
  | `playstyle(cls, ranks) -> "melee" \| "ranged" \| "caster"` | `main_tree(...) in MELEE_TREES`, `isinstance(stats, HybridStats)` row picks, `player_kind`'s hunter check |
  | `output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None) -> Output` | the `rotation_output` chain |
  | `aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor) -> tuple[float, str]` | `melee_scenarios.aoe`'s caster/melee split |
  | `facts(stats, cls, ranks) -> dict` | the `describe.rotation_facts` chain |

- **`Output` gains `pet: bool = False` and `ranged: bool = False`.** Questing's "the pet tanks" and PvP's slow pick read these instead of asking whether the class is a hunter.
- **Shared implementations live in `classes/engines.py`,** so priest, warlock and the caster side of druid/shaman don't each copy the caster adapter: `caster_output`, `caster_aoe`, `caster_facts`, `pack_aoe` (seconds from `output(pack=…)`) and a hybrid helper. The class modules bind them in a line or two each.
- **The `*_rotation.py` functions keep their signatures.** Their per-class tests (`test_<class>_aoe.py` and others) stay as they are. The adapter sits on top.
- **Out of scope:**
  - Mage, in slices 1-5 only: it joins in the mage slices below (owner, 2026-10-14: all classes should share one methodology).
  - Stat-row arithmetic in `stat_weights.py` (mage/caster/melee `apply`) is about the stat row's type, not the rotation, so it stays.
  - `group._drop_for` (Trueshot Aura) is buff data.
  - `ENGINE` stays as the report's engine switch.
- **`melee_scenarios.rotation_output` and `build_stats` stay as one-line delegates** until the last slice. That slice moves their callers to `engine()` and deletes them.

## Slices (milestone `class-engine`: #309 → #310 → #311 → #312 → #313)

1. Protocol, `engine()` and `Output` fields, plus the rogue, warrior and paladin adapters. `rotation_output` delegates for those three. (Claude writes the protocol and conformance test; a local model writes the adapters.)
2. Hunter adapter, with `pet` and `ranged` in `Output`. `_has_pet` moves into `hunter.py`. Questing downtime, the PvP slow pick and `group.player_kind` read `Output`/`playstyle`.
3. Caster and hybrid adapters (priest, warlock, druid, shaman) via `classes/engines.py`. `rotation_output`'s chain and `melee_scenarios.aoe`'s split collapse to `engine(name)` calls.
4. `facts` on every adapter, so `describe.rotation_facts` keeps only its mage branch.
5. Remaining hybrid checks (`group.py`, `report.py`) go through `playstyle`. `rotation_output` and `build_stats` are deleted, with their callers moved to `engine()`.

**Each slice is done when:**
- the full suite passes (slow included);
- `report --dataset data/datasets/1.60.1.70291.json --class <c> --out data/report-<c>.json` for the 8 non-mage classes leaves `git diff data/` empty (about 40 s per class; checked on main 2026-10-14);
- a conformance test checks that every class with `ENGINE in ("melee", "spell")` implements `ClassEngine`, from the slice that adds its adapter on.

## Mage slices (added 2026-10-14)

Owner: every class should be scored the same way. Mage was the first class and kept its own pipeline (`scenarios.py`, `mage_rotation.py`, `focus.py`, `mage_side`). The other classes were built later on a second engine that copied its conventions. The PvE references, AoE pack and 2v1 score are each written twice. The PvP score really differs: mage adds a battleground and a consensus bonus that the others don't get (#315, needs-decision).

6. #316: mage implements `ClassEngine`. Its filler choice moves inside the adapter, and `Output.spell` keeps the chosen spell in the report.
7. #317: one PvE score and one outnumbered score for every class, with one set of references.
8. #318: a class-agnostic duel `Side`. Mage builds its side in its class module, and the PvP score follows #315.

**Mage slices: the "no diff" rule changes.** A score that moves means the two engines disagreed. The PR lists each diff with its cause, and the owner approves before merge.

## One PvP formula (decision #315, 2026-10-14)

Owner chose option 1: every class gets mage's PvP score. That's the mean of the 4 world-PvP duels and the battleground, plus up to +0.10 for taking the class's consensus PvP-core talents. Non-mage PvP scores change by design. Mage's must not.

- #320: research PvP-core talents for the 8 other classes (Claude; owner's source rules; empty tier where evidence is thin)
- #321: per-class consensus tiers in `config/consensus.toml` (independent; can run any time)
- #322: battleground, survival and control scored from the shared duel `Side` (after #318)
- #323: one PvP score and the full PvP report rows for every class (after #318, #321, #322)

## Status (2026-10-15)

Slices 1-5 (#309-#313) are merged. Every scored non-mage class module implements `ClassEngine`, and all 8 non-mage reports regenerated with no diff at every step.

Where the build differs from the plan:
- `melee_scenarios.build_stats` stays, reading the engine's `playstyle`. `stat_table` still reads `MELEE_TREES` to know whether a class has a melee stat file.
- `group.player_kind` went in #313, not #310: it serves mage dungeon groups too. Mage keeps "caster" there until #316.
- qwen3.8-27b did #310, #311 and #312 (six runs, each diff matching the reference line for line). Claude applied the reference for #309 and both parts of #313 after 30-minute stalls. Splitting each reference into runs of under ~150 lines is what made the local runs work.
