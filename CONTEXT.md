# Domain glossary

Terms the code and issues use. Architecture terms (module, interface, seam, adapter, depth) follow the codebase-design vocabulary.

- **Class module**: `classes/<class>.py`. Holds the class's talent layout, talent effects and unmodeled notes, and for a scored class its engine adapter. Registered in `classes.CLASSES`.
- **Engine** (`ENGINE`): how a class is scored. `True` is mage (`scenarios.py`), `"melee"` the physical rotations, `"spell"` the caster rotation (`caster.py`), and none means unscored (routes only).
- **ClassEngine**: the interface a scored non-mage class module implements: `playstyle`, `output`, `aoe`, `facts` (docs/planning/2026-10-14-class-engine.md). Reached through `classes.engine(name)`.
- **Rotation**: a class's damage loop against one `Target`, in `classes/<class>_rotation.py` or `caster.py`. It returns a class-specific result.
- **Output**: a rotation's result in the shape the scenarios read: DPS, mana per second, out-of-mana DPS, AoE abilities, pet, ranged.
- **Playstyle**: how a build fights: `melee`, `ranged` or `caster`. A **hybrid** class (druid, shaman) has both a caster and a melee stat row (`HybridStats`), and its playstyle follows the tree holding most points (`MELEE_TREES`).
- **Scenario**: one scored situation (questing, dungeon, raid, aoe, PvP duels, outnumbered) at a checkpoint level (20/30/40/50/60).
- **Checkpoint**: a level at which every build is scored.
- **Report**: the per-class JSON (`data/report*.json`) that the dashboard renders. Its shape isn't defined in one module yet (review candidate 2).
