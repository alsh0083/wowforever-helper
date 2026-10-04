# Task #7: wowforevertalent.com fetcher

Implement `src/wowforever/sources/wowforevertalent.py` so `tests/test_source_wowforevertalent.py` passes. Do not edit tests or fixtures. Tests never touch the network.

## Page format (see `tests/fixtures/wowforevertalent/mage.html`)
- Talent data is the HTML-escaped JSON in the `props` attribute of the `<astro-island ... component-url="/_astro/Calculator.<hash>.js" ...>` element (hash changes between deploys: match `Calculator.` not the hash).
- Astro encoding: `[0]` = undefined → `None`; `[0, value]` = plain value (if it's a dict, decode each of its values); `[1, [items]]` = array (decode each item). Any other tag → `ValueError`.
- Decoded props: `gameClass` → `{id, name, source, trees: [{id, name, talents: [...], removed: [...]}]}` and `version`.
- `game_build`: the `1.60.x.y` number inside `gameClass.source` text ("... beta client, build 1.60.1.70170.").
- `page_data_version`: the first `data-version="..."` attribute in the page.

## Interface
- `decode_astro(value)`
- `@dataclass(frozen=True) WftPage`: `class_id`, `game_build`, `page_data_version`, `props_version`, `trees: list[dict]` (decoded, unchanged structure)
- `parse_page(html: str) -> WftPage`
- `class SnapshotConflict(Exception)`
- `snapshot(html: str, raw_dir: Path, *, url: str) -> Path`: writes `raw_dir/<page_data_version>/<class_id>.html` (exact bytes as UTF-8, newline unchanged: open with `newline=""`) and `manifest.json` beside it (`source`, `url`, `game_build`, `page_data_version`, `props_version`, `fetched_at` ISO UTC, `sha256` of the HTML's UTF-8 bytes; `indent=1`, sorted keys). Same content already present → return the path, write nothing. Different content at the same path → `SnapshotConflict`.
- `fetch(class_id: str, *, http_get, raw_dir: Path) -> Path`: GET `https://wowforevertalent.com/{class_id}/`, then `snapshot`.

Standard library only (`html`, `json`, `re`, `hashlib`), type hints, short docstrings.

## Done when
`.venv/Scripts/python -m pytest` passes in full.
