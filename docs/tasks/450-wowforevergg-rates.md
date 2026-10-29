# 450: wow-forever.gg talent pick rates (comparison only)

**Goal:** a new source module that reads a wow-forever.gg class talent page's pick rates by talent name, plus a
helper that lists a build's unusual picks against them (#450).

**Interface:** new file `src/wowforever/sources/wowforevergg.py` with

```python
SOURCE = "wow-forever.gg"
def pick_rates(page_html: str) -> dict[str, Any]: ...
def unusual_picks(final: Mapping[str, int], rates: Mapping[str, float], *, low: float = 15.0,
                  high: float = 60.0) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]: ...
```

**Inputs:** `tests/fixtures/wowforevergg/mage-20261029.html`; the tests read it, and you need only the facts below.

**Constraints:** standard library only (`json`, `re`, `typing`/`collections.abc`). Type hints. Module docstring:
what the page is, that the site states no license, so its numbers are for comparison only and never shown on the
dashboard (#450). Create only this module; don't edit any other file.

**Done when:** `.venv/Scripts/python -m pytest -q tests/test_wowforevergg.py` passes (3 tests).

## Page facts
- The data is the JSON inside `<script type="application/json" id="trait-data"> ... </script>` (use `re.S`).
  Keys used: `rates` (dict: node id **as a string** → float percent), `ratesBuilds` (int), `trees` (list; each
  tree has `nodes`, a list of dicts with int `id` and str `name`).
- The build: `Game data from build <strong>1.60.1.70532</strong>`; return the number as `"game_build"`.
- The window: in `<p class="calc-rates-count">From 287 of 1,312 finished ... , 13 Sept 2026 to 22 Oct 2026</p>`;
  return `"13 Sept 2026 to 22 Oct 2026"` as `"window"` (regex `(\d+ \w+ \d{4} to \d+ \w+ \d{4})` after
  `class="calc-rates-count">`).
- `pick_rates` returns `{"game_build", "window", "builds": ratesBuilds, "rates": {talent name: percent}}`.

## unusual_picks
- `rare`: talents in `final` with a rank above 0, present in `rates`, with rate strictly under `low`; sorted by
  rate ascending. Names missing from `rates` are ignored.
- `skipped`: talents in `rates` with rate at or above `high` that `final` doesn't take (missing or 0); sorted by
  rate descending.
- Each list holds `(name, rate)` tuples. Return `(rare, skipped)`.

## Steps, in this order
1. Create `src/wowforever/sources/wowforevergg.py` (regexes as module-level compiled constants).
2. Then run the Done-when command once.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; create the file with `tools/apply_patch.py` (`*** Add File:`,
  see AGENTS.md).
- Install nothing. Before the change, `tests/test_wowforevergg.py` fails to import; nothing else should fail.
- Make the edit before running any tests. Don't re-check things this spec states, don't open the fixture HTML
  (260 KB, minified), and don't create other files.
