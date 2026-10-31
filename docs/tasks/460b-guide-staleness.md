# Task #460 (part 1b): read each guide build with the calculator it was made on

Make `tests/test_wowforeverbuilds.py` pass (15 tests) without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/sources/wowforeverbuilds.py`. No network.
- Before you start, the test file fails at import (`Snapshot` and `standard_build` don't exist yet). Nothing else
  should fail.
- Each step below replaces one block with another; copy both exactly. Apply them in order, top of the file first.
- Run `.venv/Scripts/python -m pytest tests/test_wowforeverbuilds.py -q` after the last step, then the fast suite once.

## Why
A guide's build code is one digit per talent in the order of the site's calculator. If the site moves its calculator
to new trees before a guide's author updates the code, the old digits line up with the wrong talents, and the result
can still be a legal build nobody chose. The guide dates don't help: all 54 guides carry the same site-wide
`dateModified`. So the code's own history decides: a code is read with the calculator in place when the code was last
changed, using every saved snapshot of the site. The trees the build spends points in must then match ours exactly
(name, max rank, row, col), and the build must pass `rules.check_build`.

## Step 1
Replace
```python
import re
from dataclasses import dataclass

from wowforever.sources.wowforevertalent import decode_astro
```
with
```python
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from wowforever.rules import check_build
from wowforever.schema import ClassData
from wowforever.sources.wowforevertalent import decode_astro
```

## Step 2
Replace
```python
    trees: tuple[tuple[tuple[str, int], ...], ...]    # per tree, (talent name, max rank) in build-code order
```
with
```python
    trees: tuple[tuple[tuple[str, int], ...], ...]    # per tree, (talent name, max rank) in build-code order
    positions: tuple[tuple[tuple[int, int], ...], ...]  # per tree, each talent's (row, col) in the same order
```

## Step 3
Replace
```python
    def url(self) -> str:
        return f"{BASE_URL}/guide/{self.slug}"
```
with
```python
    def url(self) -> str:
        return f"{BASE_URL}/guide/{self.slug}"


@dataclass(frozen=True)
class Snapshot:
    date: str                                         # YYYY-MM-DD the site was saved
    calculators: Mapping[str, Calculator]             # by class slug
    guides: Mapping[str, GuideBuild]                  # by guide slug
```

## Step 4
Replace
```python
    trees = tuple(tuple((t["name"], int(t["maxRank"])) for t in tree["talents"]) for tree in cls["trees"])
    return Calculator(cls["slug"], build.group(1), tuple(tree["name"] for tree in cls["trees"]), trees)
```
with
```python
    trees = tuple(tuple((t["name"], int(t["maxRank"])) for t in tree["talents"]) for tree in cls["trees"])
    positions = tuple(tuple((int(t["row"]), int(t["col"])) for t in tree["talents"]) for tree in cls["trees"])
    return Calculator(cls["slug"], build.group(1), tuple(tree["name"] for tree in cls["trees"]), trees, positions)
```

## Step 5: add at the end of the file
After the last line of `guide_slugs` (`    return sorted(set(re.findall(...)))`), add two blank lines and then:
```python
def _tree(calc: Calculator, index: int) -> tuple[tuple[str, int, int, int], ...]:
    """Tree `index` of a calculator in build-code order: (name, max rank, row, col) per talent."""
    return tuple((name, rank, *pos) for (name, rank), pos in zip(calc.trees[index], calc.positions[index]))


def standard_build(slug: str, history: Sequence[Snapshot], cls: ClassData) -> tuple[dict[str, int] | None, str]:
    """The build a guide stands for on our trees, or (None, why not).

    `history` is every saved snapshot of the site, oldest first; the last is current. A code's digits follow the
    calculator in place when the code was last changed, so a code that outlived a calculator change is read with the
    old calculator. A code that changed in the same gap as its calculator is dropped unless the old calculator can't
    read it. The trees the build spends points in must match ours exactly, and the build must be legal.
    """
    latest = history[-1]
    guide = latest.guides.get(slug)
    if guide is None:
        return None, f"{slug}: not in the {latest.date} snapshot"
    first = len(history) - 1
    while first > 0:
        earlier = history[first - 1].guides.get(slug)
        if earlier is None or earlier.code != guide.code:
            break
        first -= 1
    calc = history[first].calculators[guide.class_slug]
    try:
        ranks = decode(guide.code, calc)
    except ValueError as e:
        return None, f"{slug}: {e}"
    used = [i for i, part in enumerate(guide.code.split("-")) if part.strip("0")]
```

## Step 6
Replace
```python
    used = [i for i, part in enumerate(guide.code.split("-")) if part.strip("0")]
```
with
```python
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

## Step 7: add at the end of `standard_build`
After the `return None, (f"{slug}: the build and the calculator both changed ...")` lines from step 6, add:
```python
    trees = {tree.name: tree for tree in cls.trees}
    build: dict[int, int] = {}
    for i in used:
        label = calc.tree_names[i]
        tree = trees.get(label)
        talents = {cls.talent(tid).name: cls.talent(tid) for tid in tree.talent_ids} if tree else {}
        if set(_tree(calc, i)) != {(t.name, t.max_rank, t.row, t.col) for t in talents.values()}:
            return None, (f"{slug}: {label}: the build was made on the {calc.build} calculator "
                          f"({history[first].date}), whose tree differs from ours")
        for name, _ in calc.trees[i]:
            if name in ranks:
                build[talents[name].talent_id] = ranks[name]
    errors = check_build(cls, build, cls.rules.max_level)
    if errors:
        return None, f"{slug}: not legal: " + "; ".join(errors)
    return ranks, ""
```
These lines are inside `standard_build`, at the same indent as `if first > 0:`, exactly as shown.

## Done when
- `tests/test_wowforeverbuilds.py` passes (15 tests); the fast suite has no other new failures.
- Only `src/wowforever/sources/wowforeverbuilds.py` changed.
