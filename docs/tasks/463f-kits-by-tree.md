# Task #463 (part F): each PvP opponent kit plays its tree's build, not a fixed build id

Make `tests/test_level_kits.py` and `tests/test_kit_stats.py -k plays_an_endgame` pass. Do not edit the tests or
anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/pvp/kit_stats.py`, `src/wowforever/pvp/duel.py` and
  `tools/derive_opponent_kits.py`. No network.
- Before you start, those tests fail to import `KIT_TREES` / `kit_build`.
- **Run only** `.venv/Scripts/python -m pytest tests/test_level_kits.py tests/test_kit_stats.py -q -k "plays_an_endgame or level"`.
  Do not run the fast suite or the other kit tests: the branch is mid-move to 1.60.1.70755 and their failures are
  expected until the pin moves (#463).
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.

## Why
`KIT_BUILDS` named a build id per kit, and the re-import of community standards (#460) replaces build ids. A kit
now follows its tree: of the class's endgame builds with the most points in that tree, the PvP one before the PvE
one and a community standard before a model build.

## Step 1: `src/wowforever/pvp/kit_stats.py`
Replace
```python
# kit id (config/opponents/<kit>.toml) -> community build id (config/builds/<build>.toml)
KIT_BUILDS: dict[str, str] = {
    "rogue-combat": "rogue-combat-pvp",
    "rogue-subtlety": "rogue-subtlety",
    "hunter-marksmanship": "hunter-marksmanship",
    "hunter-survival": "hunter-survival-pvp",
    "warrior-arms": "warrior-arms",
    "priest-shadow": "priest-shadow",
    "priest-discipline": "priest-discipline-smite",
    "warlock-affliction": "warlock-affliction",
    "warlock-destruction": "warlock-destruction",
    "druid-balance": "druid-balance",
    "shaman-elemental": "shaman-elemental",
    "paladin-retribution": "paladin-retribution-pvp",
    "druid-feral": "druid-feral",
    "shaman-enhancement": "shaman-enhancement",
}
```
with
```python
# kit id (config/opponents/<kit>.toml) -> community build id (config/builds/<build>.toml)
# Each kit plays its tree's build (#463): build ids change whenever the standards are re-imported (#460), trees don't.
KIT_TREES: dict[str, str] = {
    "rogue-combat": "Combat",
    "rogue-subtlety": "Subtlety",
    "hunter-marksmanship": "Marksmanship",
    "hunter-survival": "Survival",
    "warrior-arms": "Arms",
    "priest-shadow": "Shadow",
    "priest-discipline": "Discipline",
    "warlock-affliction": "Affliction",
    "warlock-destruction": "Destruction",
    "druid-balance": "Balance",
    "shaman-elemental": "Elemental",
    "paladin-retribution": "Retribution",
    "druid-feral": "Feral Combat",
    "shaman-enhancement": "Enhancement",
}
```

## Step 2: `src/wowforever/pvp/kit_stats.py`
Replace
```python
}

```
with
```python
}


def kit_build(kit_id: str, cls):
    """The build a kit plays: of the class's endgame builds with the most points in the kit's tree, the PvP one
    before the PvE one and a community standard before a model build (ties: the lowest id)."""
    tree = next(tree for tree in cls.trees if tree.name == KIT_TREES[kit_id])
    names = {t.name for t in cls.talents}

    def main_tree(build):
        if not set(build.final) <= names:
            return None
        ids = build.final_ids(cls)
        return max(cls.trees, key=lambda tr: (sum(ids.get(t, 0) for t in tr.talent_ids), -tr.tree_id)).name

    mine = [b for b in load_builds(class_name=kit_id.split("-", 1)[0])
            if b.mode != "leveling" and main_tree(b) == tree.name]
    if not mine:
        raise KeyError(f"{kit_id}: no {tree.name} build in config/builds")
    return min(mine, key=lambda b: (b.variant != "PvP", b.origin != "community", b.id))

```

## Step 3: `src/wowforever/pvp/kit_stats.py`
Replace
```python
    stats = stat_table(class_name).at(60)
    build = {b.id: b for b in load_builds(class_name=class_name)}[KIT_BUILDS[kit_id]]
    ranks = build.final_ids(cls)
```
with
```python
    stats = stat_table(class_name).at(60)
    build = kit_build(kit_id, cls)
    ranks = build.final_ids(cls)
```

## Step 4: `src/wowforever/pvp/kit_stats.py`
Replace
```python
    stats = stat_table(class_name).at(level)
    build = {b.id: b for b in load_builds(class_name=class_name)}[KIT_BUILDS[kit_id]]
    ranks = kit_ranks_at(build, cls, level)
```
with
```python
    stats = stat_table(class_name).at(level)
    build = kit_build(kit_id, cls)
    ranks = kit_ranks_at(build, cls, level)
```

## Step 5: `src/wowforever/pvp/duel.py`
Replace
```python
        return tuple(kits)
    from wowforever.pvp.kit_stats import KIT_BUILDS, engine_at   # lazy: kit_stats runs the engines
    out = []
```
with
```python
        return tuple(kits)
    from wowforever.pvp.kit_stats import KIT_TREES, engine_at   # lazy: kit_stats runs the engines
    out = []
```

## Step 6: `src/wowforever/pvp/duel.py`
Replace
```python
    for kit in kits:
        if kit.id not in KIT_BUILDS:
            out.append(kit)            # no engine build (the mage kit): level-60 values, at_level stays 60
```
with
```python
    for kit in kits:
        if kit.id not in KIT_TREES:
            out.append(kit)            # no engine build (the mage kit): level-60 values, at_level stays 60
```

## Step 7: `tools/derive_opponent_kits.py`
Replace
```python

from wowforever.pvp.kit_stats import KIT_BUILDS, engine_at_60

```
with
```python

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.pvp.kit_stats import DATASET, KIT_TREES, engine_at_60, kit_build
from wowforever.schema import Dataset

```

## Step 8: `tools/derive_opponent_kits.py`
Replace
```python
    health, dps = engine_at_60(kit_id)
    note = f"# damage engine (#147, #163), build {KIT_BUILDS[kit_id]}"
    lines = path.read_text(encoding="utf-8").split("\n")
```
with
```python
    health, dps = engine_at_60(kit_id)
    class_name = kit_id.split("-", 1)[0]
    m = class_module(class_name)
    cls, _ = attach_effects(Dataset.load(DATASET).class_data(class_name), m.TALENT_EFFECTS, m.UNMODELED)
    note = f"# damage engine (#147, #163), build {kit_build(kit_id, cls).id}"
    lines = path.read_text(encoding="utf-8").split("\n")
```

## Step 9: `tools/derive_opponent_kits.py`
Replace
```python

for kit_id in sorted(KIT_BUILDS):
    rewrite(OPPONENTS / f"{kit_id}.toml", kit_id)
```
with
```python

for kit_id in sorted(KIT_TREES):
    rewrite(OPPONENTS / f"{kit_id}.toml", kit_id)
```
