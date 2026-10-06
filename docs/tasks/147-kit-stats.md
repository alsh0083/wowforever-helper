# Task #147: rogue and hunter opponent kits from the melee engine

Make `tests/test_kit_stats.py` pass without breaking the rest of the suite. Create `src/wowforever/pvp/kit_stats.py` and `tools/derive_opponent_kits.py`, then run the tool to update four kit files. Do not edit the tests.

## Why
The rogue and hunter opponent kits in `config/opponents/` carry hand estimates for `[at_60] health` and `dps` (vs cloth). The melee engine (#111) computes them now.

## 1. `src/wowforever/pvp/kit_stats.py`
- Module docstring explaining the above.
- `KIT_BUILDS: dict[str, str]` mapping kit id to community build id:
  `rogue-combat -> rogue-combat-pvp`, `rogue-subtlety -> rogue-subtlety`, `hunter-marksmanship -> hunter-marksmanship`, `hunter-survival -> hunter-survival-pvp`.
- `engine_at_60(kit_id: str) -> tuple[float, float]` returning `(health, dps)`:
  - class name is the part of the kit id before the first `-`.
  - `m = class_module(class_name)`; `cls, _ = attach_effects(Dataset.load(DATASET).class_data(class_name), m.TALENT_EFFECTS, m.UNMODELED)` with `DATASET = <repo>/data/datasets/1.60.1.70205.json` (repo root is `Path(__file__).resolve().parents[3]`).
  - `stats = MeleeStatTable.load(class_name).at(60)`.
  - build: `{b.id: b for b in load_builds(class_name=class_name)}[KIT_BUILDS[kit_id]]`, ranks `build.final_ids(cls)`.
  - `dps = rotation_output(class_name, stats, cls.spells, cls, ranks, Target(0, cloth_armor)).dps` where `cloth_armor` is the `cloth_armor` key in `config/pvp_self.toml` (read with `tomllib`).
  - `health = stats.health`.
  - Imports: `wowforever.builds.load_builds`, `wowforever.classes.class_module`, `wowforever.effects.attach_effects`, `wowforever.melee_scenarios.MeleeStatTable, rotation_output`, `wowforever.physical.Target`, `wowforever.schema.Dataset`.

## 2. `tools/derive_opponent_kits.py`
Docstring with the run command (`.venv/Scripts/python tools/derive_opponent_kits.py`). For each kit in `KIT_BUILDS`, rewrite the `health = ...` and `dps = ...` lines under `[at_60]` in `config/opponents/<kit>.toml` with rounded integers and a trailing comment `# melee engine (#147), build <build id>`. Change only those two lines; leave everything else byte-for-byte. Print old -> new for each kit. Then change each file's header comment that says health and DPS are estimates so it says they come from the melee engine (#147).

## 3. Run it
Run the tool once so the four kit files carry the new values.

## Environment note
The package is installed in `.venv` (editable). Before you start, `tests/test_kit_stats.py` fails with an import error. Install nothing and ask for no elevation. Write edits with `tools/apply_patch.py` (see AGENTS.md). Start with `kit_stats.py`. Iterate with `.venv/Scripts/python -m pytest tests/test_kit_stats.py`. If a test elsewhere fails only on a number because the kits changed, name it in your final message and don't change it. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so and don't investigate.

## Done when
`.venv/Scripts/python -m pytest tests/test_kit_stats.py` passes and the four kit files are updated.
