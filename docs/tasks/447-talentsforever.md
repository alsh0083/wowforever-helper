# 447a: parse talentsforever.com's popular builds

**Goal:** a new source module that reads talentsforever.com's `/<class>/builds` page and decodes its build links
into talent names (#447, part A: parsing only, no network and no wiring into `update`).

**Interface:** new file `src/wowforever/sources/talentsforever.py` with

```python
SOURCE = "talentsforever.com"
def parse_builds_page(page_html: str) -> dict[str, Any]: ...
def decode_build(code: str, export: dict[str, Any]) -> dict[str, int]: ...
def popular_builds(page_html: str, export: dict[str, Any]) -> list[dict[str, Any]]: ...
```

**Inputs:** `tests/fixtures/talentsforever/mage-builds-20261029.html` (the page) and
`tests/fixtures/talentsforever/mage-export-20261027.json` (the site's CC BY export). The tests read them; you only
need the facts below.

**Constraints:** standard library only (`re`, `html`, `typing`). Type hints. Module docstring like the one in
`src/wowforever/sources/wowforevertalent.py`: what the page is, that the data is CC BY 4.0 (credit
talentsforever.com with a link), and that the shared/saved/opened numbers count from 13 Sep, before the patch, so
they are `*_total` and must never feed the 20-save "settled" rule (#447). Create only the module; don't edit
any other file.

**Done when:** `.venv/Scripts/python -m pytest -q tests/test_talentsforever.py` passes (5 tests).

## Page facts
- The window sentence appears in the page as `since the Oct 20 hotfixes to build 70425`. `parse_builds_page`
  returns it as `"window"` (from "since the" up to and including the build number) and the number alone as
  `"window_build"` (string `"70425"`). One regex: `since the [^.,<]*? to build (\d+)`.
- The top-5 list is the **first** `<ol class="rows">...</ol>` in the page. Each row is one `<li>...</li>`:
  - `<span class="rank">1</span>`: the rank, an int.
  - `<h3 class="bn">Arcane Mage 47/4/0</h3>`: the name.
  - `Arcane <i></i>47 <i>/</i> Fire <i></i>4 <i>/</i> Frost <i></i>0`: the points; the numbers right after
    `<i></i>`, as a list of 3 ints.
  - Text `shared 60 · saved 168 · opened 1,033 · across 47 close builds` (strip tags with
    `re.sub("<[^>]+>", "", ...)` and `html.unescape` first; numbers can have commas): keys `shared_total`,
    `saved_total`, `opened_total`, `variants` (the "across N" number).
  - `<a class="load" href="/mage/60/2551225223122301531-13--8">`: `"code"` is the part after `/60/`.
- Return `{"window": ..., "window_build": ..., "top": [row, ...]}` with each row exactly the keys
  `rank, name, points, shared_total, saved_total, opened_total, variants, code`.

## Code facts
- `export["talents"]["trees"]` is a list of 3 trees; each has `"talents"`, a list of dicts with `"name"`.
- A code is the three trees' digit strings joined by `-`, then a trailing segment (ignore it). Digit *i* of tree
  *t* is the rank of `export["talents"]["trees"][t]["talents"][i]`. An empty segment means no points there.
- `decode_build` returns `{talent name: rank}` for ranks above 0 only.
- `popular_builds` returns each row of `parse_builds_page(...)["top"]` with one more key, `"final"`: the decoded
  code.

## Steps, in this order
1. Create `src/wowforever/sources/talentsforever.py` with the module docstring, `SOURCE`, and the three functions
   (the regexes as module-level compiled constants, as `wowforevertalent.py` does).
2. Then run the Done-when command once.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; create the file with `tools/apply_patch.py` (`*** Add File:`,
  see AGENTS.md).
- Install nothing. Before the change, `tests/test_talentsforever.py` fails to import; nothing else should fail.
- Make the edit before running any tests. Don't re-check things this spec states, don't open the fixture HTML
  (it is long and minified), and don't create other files.
