"""Fetcher for wowforevertalent.com class pages.

The site's talent calculator (Astro) embeds each class's data as an HTML-escaped JSON
`props` blob on an <astro-island> element whose component-url is /_astro/Calculator.<hash>.js
(the hash changes per deploy). Values use Astro's tagged encoding: [0] = undefined,
[0, value] = plain value, [1, [items]] = array. Data is CC-BY: keep attribution in the
README and dashboard footer.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from wowforever.sources.http import http_get as default_http_get

SOURCE = "wowforevertalent.com"
BASE_URL = "https://wowforevertalent.com"

_CALCULATOR_ELEMENT = re.compile(r'component-url="/_astro/Calculator\.[^"]+\.js"')
_PROPS_ATTRIBUTE = re.compile(r'\bprops="([^"]*)"')
_DATA_VERSION = re.compile(r'data-version="([^"]*)"')
_GAME_BUILD = re.compile(r"1\.60\.\d+\.\d+")


class SnapshotConflict(Exception):
    """A snapshot path already holds different content than the page to save."""


def decode_astro(value: Any) -> Any:
    """Decode one value of Astro's island encoding; non-list values pass through."""
    if not isinstance(value, list):
        return value
    tag, rest = value[0], value[1:]
    if tag == 0:
        if not rest:
            return None
        decoded = rest[0]
        if isinstance(decoded, dict):
            return {key: decode_astro(item) for key, item in decoded.items()}
        return decoded
    if tag == 1:
        return [decode_astro(item) for item in rest[0]]
    raise ValueError(f"unsupported Astro tag {tag!r}")


@dataclass(frozen=True)
class WftPage:
    """One class page: decoded calculator props plus the page's version markers."""

    class_id: str
    game_build: str
    page_data_version: str
    props_version: str
    trees: list[dict[str, Any]]


def parse_page(page_html: str) -> WftPage:
    """Extract the Calculator island's decoded props and version markers from a page."""
    marker = _CALCULATOR_ELEMENT.search(page_html)
    if marker is None:
        raise ValueError("no Calculator astro-island element in page")
    element_start = page_html.rfind("<astro-island", 0, marker.start())
    props_match = _PROPS_ATTRIBUTE.search(page_html[element_start:])
    if props_match is None:
        raise ValueError("Calculator astro-island has no props attribute")
    props = json.loads(html.unescape(props_match.group(1)))
    game_class = decode_astro(props["gameClass"])
    build_match = _GAME_BUILD.search(str(game_class.get("source", "")))
    if build_match is None:
        raise ValueError("no 1.60.x.y build number in gameClass.source")
    version_match = _DATA_VERSION.search(page_html)
    if version_match is None:
        raise ValueError("no data-version attribute in page")
    return WftPage(
        class_id=game_class["id"],
        game_build=build_match.group(0),
        page_data_version=version_match.group(1),
        props_version=decode_astro(props["version"]),
        trees=game_class["trees"],
    )


def snapshot(page_html: str, raw_dir: Path, *, url: str) -> Path:
    """Save a class page snapshot plus its manifest; idempotent for identical content.

    Writes raw_dir/<page_data_version>/<class_id>.html with the page's exact UTF-8 bytes
    and a manifest.json beside it. Same content already present returns the path
    untouched; different content at the same path raises `SnapshotConflict`.
    """
    page = parse_page(page_html)
    path = raw_dir / page.page_data_version / f"{page.class_id}.html"
    if path.exists():
        if path.read_bytes() == page_html.encode("utf-8"):
            return path
        raise SnapshotConflict(f"{path} already holds different content")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(page_html)
    manifest = {
        "source": SOURCE,
        "url": url,
        "game_build": page.game_build,
        "page_data_version": page.page_data_version,
        "props_version": page.props_version,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(page_html.encode("utf-8")).hexdigest(),
    }
    (path.parent / "manifest.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8"
    )
    return path


def fetch(class_id: str, *, http_get: Callable[[str], str] | None = None, raw_dir: Path) -> Path:
    """Download one class page and snapshot it under raw_dir."""
    if http_get is None:
        http_get = default_http_get
    url = f"{BASE_URL}/{class_id}/"
    return snapshot(http_get(url), raw_dir, url=url)
