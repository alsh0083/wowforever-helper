# Task #460 (part 1c): when a guide's code and the calculator changed in the same gap, let the evidence decide

Make `tests/test_wowforeverbuilds.py` pass (21 tests) without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/sources/wowforeverbuilds.py`. No network.
- Before you start, the test file fails at import (`calculator_errors` and `title_misses` don't exist yet). Nothing
  else should fail.
- Each step below replaces one block with another; copy both exactly. Apply them in order, top of the file first.
- Run `.venv/Scripts/python -m pytest tests/test_wowforeverbuilds.py -q` after the last step, then the fast suite once.

## Why
`standard_build` drops a guide whose code and calculator both changed between two saved snapshots, because it can't
tell which trees the code was written for. Long gaps between update checks make that common. Instead, read the code
with both calculators and keep a reading only if it is legal on that calculator's own trees (5 points per earlier row,
prerequisites from the calculator's `requires`) and takes every talent the guide's title names. Keep the guide when
exactly one reading counts, or when both count and give the same talents. On today's 54 guides, every reading passes
both checks on its own calculator, and no title names a talent its build skips.

## Step 1
Replace
```python
from collections.abc import Mapping, Sequence
```
with
```python
from collections.abc import Iterable, Mapping, Sequence
```

## Step 2
Replace
```python
BASE_URL = "https://wowforeverbuilds.com"
```
with
```python
BASE_URL = "https://wowforeverbuilds.com"
ROW_POINTS = 5                                        # points spent in a tree's earlier rows per row
```

## Step 3
Replace
```python
    positions: tuple[tuple[tuple[int, int], ...], ...]  # per tree, each talent's (row, col) in the same order
```
with
```python
    positions: tuple[tuple[tuple[int, int], ...], ...]  # per tree, each talent's (row, col) in the same order
    requires: tuple[tuple[tuple[int, int] | None, ...], ...]  # per tree, (index in the tree, rank) each talent needs
```

## Step 4
Replace
```python
    return Calculator(cls["slug"], build.group(1), tuple(tree["name"] for tree in cls["trees"]), trees, positions)
```
with
```python
    requires = tuple(_requires(tree["talents"]) for tree in cls["trees"])
    return Calculator(cls["slug"], build.group(1), tuple(tree["name"] for tree in cls["trees"]), trees, positions,
                      requires)


def _requires(talents: list[dict]) -> tuple[tuple[int, int] | None, ...]:
    """Each talent's prerequisite as (index of the required talent in the same tree, rank), or None."""
    index = {t["id"]: i for i, t in enumerate(talents)}
    out: list[tuple[int, int] | None] = []
    for t in talents:
        needs = t.get("requires") or []
        if len(needs) > 1 or any(n["id"] not in index for n in needs):
            raise ValueError(f"{t['name']}: unsupported prerequisite {needs!r}")
        out.append((index[needs[0]["id"]], int(needs[0]["ranks"])) if needs else None)
    return tuple(out)
```

## Step 5
Replace
```python
def standard_build(slug: str, history: Sequence[Snapshot], cls: ClassData) -> tuple[dict[str, int] | None, str]:
```
with
```python
def calculator_errors(ranks: Mapping[str, int], calc: Calculator) -> list[str]:
    """What breaks a decoded build on the calculator's own trees: 5 points per row above, and prerequisites."""
    errors: list[str] = []
    for label, tree, pos, needs in zip(calc.tree_names, calc.trees, calc.positions, calc.requires):
        points = [ranks.get(name, 0) for name, _ in tree]
        for (name, _), (row, _), need, taken in zip(tree, pos, needs, points):
            if not taken:
                continue
            spent = sum(p for p, (r, _) in zip(points, pos) if r < row)
            if spent < ROW_POINTS * row:
                errors.append(f"{label}/{name}: needs {ROW_POINTS * row} points in earlier rows, has {spent}")
            if need is not None and points[need[0]] < need[1]:
                errors.append(f"{label}/{name}: needs {tree[need[0]][0]} at rank {need[1]}")
    return errors


def title_misses(ranks: Mapping[str, int], title: str, names: Iterable[str]) -> list[str]:
    """Talents among `names` that a guide's title names but its build doesn't take, sorted. Longer names match
    first, so "Bite" inside "Primal Bite" isn't a mention of Bite."""
    named = []
    for name in sorted(set(names), key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(name) + r"(?!\w)"
        if re.search(pattern, title, re.IGNORECASE):
            named.append(name)
            title = re.sub(pattern, "|", title, flags=re.IGNORECASE)
    return sorted(name for name in named if name not in ranks)


def _changed(a: Calculator, b: Calculator, used: Sequence[int]) -> bool:
    return any(i >= len(a.trees) or i >= len(b.trees) or _tree(a, i) != _tree(b, i) for i in used)


def standard_build(slug: str, history: Sequence[Snapshot], cls: ClassData) -> tuple[dict[str, int] | None, str]:
```

## Step 6: the docstring of `standard_build`
Replace
```python
    old calculator. A code that changed in the same gap as its calculator is dropped unless the old calculator can't
    read it. The trees the build spends points in must match ours exactly, and the build must be legal.
```
with
```python
    old calculator. When a code changed in the same gap as its calculator, each calculator reads it, and a reading
    counts only if it is legal on that calculator's trees and takes every talent the guide's title names; the guide
    is kept only when exactly one reading counts, or both count and agree. The trees the build spends points in must
    then match ours exactly, and the build must be legal.
```

## Step 7
Replace
```python
    calc = history[first].calculators[guide.class_slug]
    try:
        ranks = decode(guide.code, calc)
    except ValueError as e:
        return None, f"{slug}: {e}"
    used = [i for i, part in enumerate(guide.code.split("-")) if part.strip("0")]
    if first > 0:
        before = history[first - 1].calculators[guide.class_slug]
        if any(_tree(before, i) != _tree(calc, i) for i in used):
            try:
                decode(guide.code, before)
            except ValueError:
                pass
            else:
                return None, (f"{slug}: the build and the calculator both changed between {history[first - 1].date} "
                              f"and {history[first].date}; can't tell which trees it was made on")
```
with
```python
    calc = history[first].calculators[guide.class_slug]
    made_on = history[first].date
    used = [i for i, part in enumerate(guide.code.split("-")) if part.strip("0")]
    before = history[first - 1].calculators[guide.class_slug] if first > 0 else None
    if before is not None and _changed(before, calc, used):
        names = [name for c in (before, calc) for tree in c.trees for name, _ in tree]
        readings = []
        for when, c in ((history[first - 1].date, before), (made_on, calc)):
            try:
                r = decode(guide.code, c)
            except ValueError:
                continue
            if not calculator_errors(r, c) and not title_misses(r, guide.title, names):
                readings.append((when, c, r))
        if len(readings) == 2 and readings[0][2] == readings[1][2]:
            readings = readings[1:]                   # both read the same talents: which one doesn't matter
        if len(readings) != 1:
            outcome = "two different plausible builds" if readings else "no plausible build"
            return None, (f"{slug}: the build and the calculator both changed between {history[first - 1].date} "
                          f"and {made_on}, and the two calculators read it as {outcome}")
        made_on, calc, ranks = readings[0]
    else:
        try:
            ranks = decode(guide.code, calc)
        except ValueError as e:
            return None, f"{slug}: {e}"
```

## Step 8
Replace
```python
                          f"({history[first].date}), whose tree differs from ours")
```
with
```python
                          f"({made_on}), whose tree differs from ours")
```

## Done when
- `tests/test_wowforeverbuilds.py` passes (21 tests); the fast suite has no other new failures.
- Only `src/wowforever/sources/wowforeverbuilds.py` changed.
