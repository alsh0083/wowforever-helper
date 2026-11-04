# Task #456 (part B1): write a build's tables with the hotfixes applied

Make `tests/test_hotfixes.py` pass (12 tests) without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/sources/hotfixes.py`.
- Before you start, the three new tests at the end of `tests/test_hotfixes.py` fail (`table_hash`, `overlay_build` don't exist yet); the other nine pass.
- Run `.venv/Scripts/python -m pytest tests/test_hotfixes.py -q` after each step, then the fast suite once.

## Why
`update` reads a build's tables from `data/cache/wago/<build>/` (one CSV per table, plus `db2/<table>.db2` and `.dbd`).
To build a dataset of "70707 + hotfixes", the same CSVs are written to another folder with the hotfix rows applied
(`apply_csv`, already in this file). A hotfix names its table by the table hash in the `.db2` header.

## Step 1: imports
Change `from collections.abc import Iterable` to `from collections.abc import Iterable, Sequence`, and after
`from dataclasses import dataclass` add the line `from pathlib import Path`.

## Step 2: add at the end of the file
```python
def table_hash(db2_data: bytes) -> int:
    """The table hash in a WDC5 file's header (what a hotfix entry names its table by)."""
    return db2.HEADER.unpack_from(db2_data, 0)[7]
```

## Step 3: add at the end of the file
```python
def overlay_build(build_dir: Path, out_dir: Path, build: str, hotfixes: Sequence[Hotfix]) -> list[str]:
    """Write every table CSV of a cached build to `out_dir` with the hotfixes applied. Tables with a game file and
    definition (`db2/<table>.db2`, `.dbd`) get their rows changed; the rest are copied. Returns the changed tables."""
    out_dir.mkdir(parents=True, exist_ok=True)
    changed = []
    for csv_path in sorted(build_dir.glob("*.csv")):
        text = csv_path.read_text(encoding="utf-8")
        db2_path = build_dir / "db2" / f"{csv_path.stem}.db2"
        dbd_path = build_dir / "db2" / f"{csv_path.stem}.dbd"
        if db2_path.exists() and dbd_path.exists():
            data = db2_path.read_bytes()
            schema = db2.schema_for(db2.parse_dbd(dbd_path.read_text(encoding="utf-8")), build, db2.layout_hash(data))
            new_text = apply_csv(text, schema, table_hash(data), hotfixes)
            if new_text != text:
                changed.append(csv_path.stem)
                text = new_text
        (out_dir / csv_path.name).write_text(text, encoding="utf-8", newline="")
    return changed
```

## Done when
- `tests/test_hotfixes.py` passes (12 tests); the fast suite has no other new failures.
- Only `src/wowforever/sources/hotfixes.py` changed.
