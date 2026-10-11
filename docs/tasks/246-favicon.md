# Task #246: WoW Forever icon in the browser tab

Make `tests/test_favicon.py` pass without breaking the rest of the suite. Edit `src/wowforever/dashboard.py`, `dashboard/template.html` and `src/wowforever/__main__.py` only. Do not edit the tests, and do not touch `dashboard/favicon.png` or `dashboard/index.html`.

## Why
The page has no tab icon. `dashboard/favicon.png` (already committed) is the game client's WoW Forever badge. It's inlined like the faction emblems, so the page keeps working offline.

## 1. `dashboard/template.html`
Right after the `<title>` line in `<head>`, add these two lines:
```
<!-- tab icon: the game client's interface/glues/common/glues-wow-foreverlogo-infinity.blp (fdid 8363869; build 1.60.1.70338) via wago.tools' published /api/casc, cropped to the badge; dashboard/favicon.png -->
<!--__FAVICON__-->
```

## 2. `src/wowforever/dashboard.py`
- `FAVICON = TEMPLATE.parent / "favicon.png"`, next to `TEMPLATE`.
- `render()` gains a keyword argument `favicon: bytes | None = None`. Add `"<!--__FAVICON__-->"` to the placeholders it checks for. Replace it with `<link rel="icon" type="image/png" href="data:image/png;base64,{base64}">` when `favicon` is given, and with an empty string when it isn't.

## 3. `src/wowforever/__main__.py`
In the `dashboard` command, pass `favicon=FAVICON.read_bytes() if FAVICON.exists() else None` to `render`, importing `FAVICON` from `wowforever.dashboard` alongside `fetch_icons` and `render`.

## Environment note
The package is already installed in `.venv` (editable). Before you start, `tests/test_favicon.py` fails at collection with `ImportError: cannot import name 'FAVICON'`. That's the expected failure. Install nothing and ask for no elevation. There is no network: don't run `wowforever dashboard`. Write edits with `tools/apply_patch.py` (see AGENTS.md); `template.html` has very long lines, so add the two new lines as their own hunk after the `<title>` line and change nothing else in that file. Iterate with `.venv/Scripts/python -m pytest tests/test_favicon.py tests/test_dashboard.py`. If tests that use `tmp_path` error with permission or path errors, that's the sandbox: say so in your final message and don't investigate.

## Done when
`.venv/Scripts/python -m pytest tests/test_favicon.py tests/test_dashboard.py tests/test_dashboard_classes.py` passes.
