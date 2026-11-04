# Task #463 (part H): the seed tool also fills recognized hybrids, and consensus tiers accept renamed talents

Make `tests/test_consensus.py -k checked_against` pass, and leave `tools/seed_tree_builds.py` compiling. Do not edit
the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `tools/seed_tree_builds.py` and `src/wowforever/consensus.py`. No network. Do not run the
  seed tool.
- **Run only** `.venv/Scripts/python -m pytest tests/test_consensus.py -q -k checked_against` and
  `.venv/Scripts/python -m py_compile tools/seed_tree_builds.py`. The fast suite is mid-move to 70755: its other
  failures are expected.
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.

## Why
- The owner asked (2026-10-05) that every matrix slot hold a build. After the 70755 re-import (#460), no source
  publishes the hybrid slots (mage Fire/Frost and Arcane/Fire, rogue Assassination/Subtlety), so the seed tool fills
  them too: the first tree up to 30 points, then the second, then the usual top-up and hill-climb.
- A tier that names a talent by its pre-patch name (the guide's "Elemental Precision", now "Precision") is still
  that talent: names in `config/talent_renames.toml` count.

## Step 1: `tools/seed_tree_builds.py`
Replace
```python
"""A PvE model build for every deep tree no endgame build covers yet (#460, #463).

```
with
```python
"""A PvE model build for every deep tree and recognized hybrid no endgame build covers yet (#460, #463).

```

## Step 2: `tools/seed_tree_builds.py`
Replace
```python

def fill_tree(cls, tree, fn):
    """Points into `tree` one at a time, best score first, while a legal point is left there."""
    ranks: dict[int, int] = {}
    while sum(ranks.values()) < points_available(60, cls.rules):
        options = []
```
with
```python

def fill_tree(cls, tree, fn, ranks=None, limit=None):
    """Points into `tree` one at a time, best score first, while a legal point is left there (and, with `limit`,
    until the tree holds that many)."""
    ranks = dict(ranks or {})
    total = points_available(60, cls.rules)
    while sum(ranks.values()) < total and (limit is None or sum(ranks.get(t, 0) for t in tree.talent_ids) < limit):
        options = []
```

## Step 3: `tools/seed_tree_builds.py`
Replace
```python
        cls, _ = attach_effects(ds.class_data(c), m.TALENT_EFFECTS, m.UNMODELED)
        recognized = tuple(getattr(m, "HYBRIDS", ()))
        covered = set()
```
with
```python
        cls, _ = attach_effects(ds.class_data(c), m.TALENT_EFFECTS, m.UNMODELED)
        # the mage report reads its hybrids from config/consensus.toml, the other classes from their module
        recognized = tuple(getattr(m, "HYBRIDS", arch["recognized"] if c == "mage" else ()))
        covered = set()
```

## Step 4: `tools/seed_tree_builds.py`
Replace
```python
        fn = lambda r, c=c, cls=cls, stats=stats: pve_score(c, stats, cls.spells, cls, r)
        for tree in cls.trees:
            archetype = f"deep {tree.name}"
            if archetype in covered:
```
with
```python
        fn = lambda r, c=c, cls=cls, stats=stats: pve_score(c, stats, cls.spells, cls, r)
        trees = {tree.name: tree for tree in cls.trees}
        targets = [(f"deep {tree.name}", (tree,)) for tree in cls.trees]
        targets += [(hybrid, tuple(trees[n] for n in hybrid.split("/"))) for hybrid in recognized]
        for archetype, parts in targets:
            if archetype in covered:
```

## Step 5: `tools/seed_tree_builds.py`
Replace
```python
                continue
            ranks = top_up(cls, fill_tree(cls, tree, fn), fn)
            best, _ = improve(cls, ranks, fn, archetype=archetype, deep=arch["deep"], hybrid=arch["hybrid"],
```
with
```python
                continue
            if len(parts) == 1:
                ranks = fill_tree(cls, parts[0], fn)
            else:                      # a hybrid: its first tree up to 30 points, then its second
                ranks = fill_tree(cls, parts[1], fn, fill_tree(cls, parts[0], fn, limit=30))
            ranks = top_up(cls, ranks, fn)
            best, _ = improve(cls, ranks, fn, archetype=archetype, deep=arch["deep"], hybrid=arch["hybrid"],
```

## Step 6: `tools/seed_tree_builds.py`
Replace
```python
            names = {t.talent_id: t.name for t in cls.talents}
            slug = tree.name.lower().replace(" ", "-")
            write(c, f"{c}-{slug}-pve", archetype, "PvE", {names[t]: r for t, r in best.items() if r},
```
with
```python
            names = {t.talent_id: t.name for t in cls.talents}
            slug = archetype.removeprefix("deep ").lower().replace("/", "-").replace(" ", "-")
            write(c, f"{c}-{slug}-pve", archetype, "PvE", {names[t]: r for t, r in best.items() if r},
```

## Step 7: `src/wowforever/consensus.py`
Replace
```python

from wowforever.schema import ClassData
from wowforever.toml_cache import load_toml
```
with
```python

from wowforever.schema import ClassData, talent_aliases
from wowforever.toml_cache import load_toml
```

## Step 8: `src/wowforever/consensus.py`
Replace
```python
                if cls is not None and cls.class_name == class_name:
                    known = {x.name for x in cls.talents}
                    out += [f"tiers.{class_name}.{name}: {n!r} is not a talent" for tier in TIERS
```
with
```python
                if cls is not None and cls.class_name == class_name:
                    known = {a for x in cls.talents for a in talent_aliases(x.name)}   # renames count (#463)
                    out += [f"tiers.{class_name}.{name}: {n!r} is not a talent" for tier in TIERS
```

## Step 9: `src/wowforever/consensus.py`
Replace
```python
                    out += [f"tiers.{class_name}.{name}: {n!r} is not a talent" for tier in TIERS
                            for n in t.get(tier, ()) if n not in known]
        return out
```
with
```python
                    out += [f"tiers.{class_name}.{name}: {n!r} is not a talent" for tier in TIERS
                            for n in t.get(tier, ()) if n.lower() not in known]
        return out
```
