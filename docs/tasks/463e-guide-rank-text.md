# Task #463 (part E): guide builds must match our rank text, not only our tree layout

Make `tests/test_wowforeverbuilds.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/sources/wowforeverbuilds.py`. No network.
- Before you start, the four tests after "#463: a build picked for other numbers" fail; the other 26 pass.
- `tests/test_rules_70755.py` may fail in the fast suite; that is expected (other tasks), leave it alone.
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.
- Run `.venv/Scripts/python -m pytest tests/test_wowforeverbuilds.py -q` at the end, then the fast suite once.

## Why
wowforeverbuilds.com's guides were picked on its calculator's talent numbers. The guard already drops a guide whose
tree layout differs from ours; a talent can keep its name and place and still change its numbers (70707 changed 219
talents). The calculator page carries every rank's text, so the guard now compares it too, over the trees the build
spends points in.

## Step 1: `src/wowforever/sources/wowforeverbuilds.py`
Replace
```python
    requires: tuple[tuple[tuple[int, int] | None, ...], ...]  # per tree, (index in the tree, rank) each talent needs

```
with
```python
    requires: tuple[tuple[tuple[int, int] | None, ...], ...]  # per tree, (index in the tree, rank) each talent needs
    texts: tuple[tuple[tuple[str, ...], ...], ...] = ()  # per tree, each talent's rank text (#463); () when unknown

```

## Step 2: `src/wowforever/sources/wowforeverbuilds.py`
Replace
```python
    requires = tuple(_requires(tree["talents"]) for tree in cls["trees"])
    return Calculator(cls["slug"], build.group(1), tuple(tree["name"] for tree in cls["trees"]), trees, positions,
```
with
```python
    requires = tuple(_requires(tree["talents"]) for tree in cls["trees"])
    texts = tuple(tuple(tuple(r["description"] for r in t["ranks"]) for t in tree["talents"]) for tree in cls["trees"])
    return Calculator(cls["slug"], build.group(1), tuple(tree["name"] for tree in cls["trees"]), trees, positions,
```

## Step 3: `src/wowforever/sources/wowforeverbuilds.py`
Replace
```python
    return Calculator(cls["slug"], build.group(1), tuple(tree["name"] for tree in cls["trees"]), trees, positions,
                      requires)

```
with
```python
    return Calculator(cls["slug"], build.group(1), tuple(tree["name"] for tree in cls["trees"]), trees, positions,
                      requires, texts)

```

## Step 4: `src/wowforever/sources/wowforeverbuilds.py`
Replace
```python

def standard_build(slug: str, history: Sequence[Snapshot], cls: ClassData) -> tuple[dict[str, int] | None, str]:
```
with
```python

def _words(text: str) -> str:
    """Rank text compared word for word: spacing and a final full stop don't count."""
    return " ".join(text.split()).rstrip(".")


def standard_build(slug: str, history: Sequence[Snapshot], cls: ClassData) -> tuple[dict[str, int] | None, str]:
```

## Step 5: `src/wowforever/sources/wowforeverbuilds.py`
Replace
```python
    is kept only when exactly one reading counts, or both count and agree. The trees the build spends points in must
    then match ours exactly, and the build must be legal.
    """
```
with
```python
    is kept only when exactly one reading counts, or both count and agree. The trees the build spends points in must
    then match ours exactly, in layout and in every talent's rank text (a build picked for other numbers isn't a
    current standard, #463), and the build must be legal.
    """
```

## Step 6: `src/wowforever/sources/wowforeverbuilds.py`
Replace
```python
                          f"({made_on}), whose tree differs from ours")
        for name, _ in calc.trees[i]:
```
with
```python
                          f"({made_on}), whose tree differs from ours")
        changed = [name for (name, _), text in zip(calc.trees[i], calc.texts[i] if calc.texts else ())
                   if tuple(map(_words, text)) != tuple(map(_words, talents[name].rank_text))]
        if changed:
            return None, (f"{slug}: {label}: the build was made on the {calc.build} calculator ({made_on}), "
                          f"whose rank text differs from ours for " + ", ".join(changed))
        for name, _ in calc.trees[i]:
```
