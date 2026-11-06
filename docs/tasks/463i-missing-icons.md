# Task #463 (part I): the dashboard leaves out an icon the CDN doesn't have

Make `tests/test_dashboard.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/dashboard.py`. No network.
- Before you start, `test_fetch_icons_leaves_out_an_icon_the_cdn_doesnt_have` fails; the other tests pass.
- Each step replaces one block with another; copy both exactly, including blank lines. Apply them in order.
- Run `.venv/Scripts/python -m pytest tests/test_dashboard.py -q` at the end, then the fast suite once.

## Why
Three 1.60.1.70755 talents use icons the icon CDN lacks (`ability_creature_cursed_02`, `ability_rogue_blackjack`,
`inv_sword_32`), and `wowforever dashboard` stops on the 404. A missing icon is left out (the page draws the talent
without one); any other HTTP error still fails.


## Step 1: `src/wowforever/dashboard.py`
Replace
```python
import json
from collections.abc import Mapping, Sequence
```
with
```python
import json
import urllib.error
from collections.abc import Mapping, Sequence
```

## Step 2: `src/wowforever/dashboard.py`
Replace
```python
            continue
        data = http_get_bytes(ICON_URL.format(name))
        path.parent.mkdir(parents=True, exist_ok=True)
```
with
```python
            continue
        try:
            data = http_get_bytes(ICON_URL.format(name))
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            continue                 # the CDN has no such icon: the talent is drawn without one (#463)
        path.parent.mkdir(parents=True, exist_ok=True)
```
