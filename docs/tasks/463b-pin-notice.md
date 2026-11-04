# Task #463 (part B): a dashboard notice while the model reads an older build

Make `tests/test_dashboard.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/dashboard.py`, `dashboard/template.html` and `src/wowforever/__main__.py`. No network.
- Before you start, the three `pin_notice` / notice tests at the end of `tests/test_dashboard.py` fail; the others pass.
- Each step replaces one block with another; copy both exactly. `dashboard/template.html` has very long lines:
  for steps 4 and 5 use a short Python script with `str.replace` (read and write UTF-8, keep the line ends) instead
  of a patch hunk.
- Run `.venv/Scripts/python -m pytest tests/test_dashboard.py -q` at the end, then the fast suite once.

## Why
The model reads the build pinned in `config/dataset.toml` (1.60.1.70425) while newer builds are saved (1.60.1.70755).
The page must say so instead of presenting old numbers as current.

## Step 1: `src/wowforever/dashboard.py`
Replace
```python
def render(payload: dict | Sequence[dict], icons: Mapping[str, bytes], *, gear: Mapping | None = None,
           gear_rules: Mapping | None = None, favicon: bytes | None = None) -> str:
```
with
```python
ISSUES_URL = "https://github.com/alsh0083/wowforever-helper/issues/"


def pin_notice(pinned: str, newest: str, issue: str) -> str:
    """A notice for the top of the page while the model reads an older build than the newest saved one (#463)."""
    if tuple(map(int, pinned.split("."))) >= tuple(map(int, newest.split("."))):
        return ""
    link = (f'<a href="{ISSUES_URL}{issue.lstrip("#")}" target="_blank" rel="noopener noreferrer">'
            f'{html.escape(issue)}</a>')
    return (f'<div class="pin-notice" role="status">Scores are from game build {html.escape(pinned)}. '
            f'Build {html.escape(newest)} is out, and moving the model to it is in progress: {link}.</div>')


def render(payload: dict | Sequence[dict], icons: Mapping[str, bytes], *, gear: Mapping | None = None,
           gear_rules: Mapping | None = None, favicon: bytes | None = None, notice: str = "") -> str:
```

## Step 2: `src/wowforever/dashboard.py`
Replace
```python
                        "<!--__FAVICON__-->"):
```
with
```python
                        "<!--__FAVICON__-->", "<!--__NOTICE__-->"):
```

## Step 3: `src/wowforever/dashboard.py`
Replace
```python
            .replace("<!--__FAVICON__-->", favicon_html))
```
with
```python
            .replace("<!--__FAVICON__-->", favicon_html)
            .replace("<!--__NOTICE__-->", notice))
```

## Step 4: `dashboard/template.html`
Replace the text `<div class="edition" id="edition"></div></header>` with
`<div class="edition" id="edition"></div></header><!--__NOTICE__-->`.

## Step 5: `dashboard/template.html`
Replace the text `.class-tabs{display:flex;` with
`.pin-notice{margin:8px 16px;padding:8px 12px;border:1px solid #c9a227;border-radius:6px;background:rgba(201,162,39,.12);font-size:13px;line-height:1.4}.pin-notice a{color:inherit;text-decoration:underline}.class-tabs{display:flex;`

## Step 6: `src/wowforever/__main__.py`
Replace
```python
        out.write_text(render(reports, icons, gear=gear, gear_rules=rules, favicon=FAVICON.read_bytes() if FAVICON.exists() else None), encoding="utf-8", newline="\n")
```
with
```python
        import re

        from wowforever.dashboard import pin_notice
        from wowforever.schema import DATASET_PIN, latest_dataset_path, newest_saved_dataset

        tracked = re.findall(r"tracked in (#\d+)", DATASET_PIN.read_text(encoding="utf-8"))
        notice = pin_notice(latest_dataset_path().stem, newest_saved_dataset().stem, tracked[-1] if tracked else "#463")
        out.write_text(render(reports, icons, gear=gear, gear_rules=rules, favicon=FAVICON.read_bytes() if FAVICON.exists() else None, notice=notice), encoding="utf-8", newline="\n")
```

## Done when
- `tests/test_dashboard.py` passes; the fast suite has no other new failures.
- Only the three files above changed.
