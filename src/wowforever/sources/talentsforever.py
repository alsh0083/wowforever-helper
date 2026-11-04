"""Parser for talentsforever.com's <class>/builds pages and their build codes.

The site lists each class's most shared builds as a top-5 table: rank, name,
tree points, and shared/saved/opened counters per row, each linking to the
build's code. A code is the three trees' rank-digit strings joined by "-"
plus a trailing segment: tree t's digit i is the rank of the i-th talent of
export["talents"]["trees"][t]["talents"], an empty segment taking none, so a
code decodes against the site's JSON talent export. Page data and the export
are CC BY 4.0: keep the credit to talentsforever.com (https://talentsforever.com)
in the README and dashboard footer. The shared/saved/opened counters count
from 13 Sep, before the Oct 20 hotfix, so they are exposed as *_total and
must never feed the 20-save "settled" rule (#447).
"""

from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

SOURCE = "talentsforever.com"

_WINDOW_RE = re.compile(r"since the [^.,<]*? to build (\d+)")
_TOP_LIST_RE = re.compile(r'<ol class="rows"[^>]*>.*?</ol>', re.DOTALL)
_ROW_RE = re.compile(r"<li[^>]*>.*?</li>", re.DOTALL)
_RANK_RE = re.compile(r'<span class="rank">(\d+)</span>')
_NAME_RE = re.compile(r'<h3 class="bn">(.*?)</h3>', re.DOTALL)
_POINTS_RE = re.compile(r"<i></i>(\d+)")
_SHARED_RE = re.compile(r"shared ([\d,]+)")
_SAVED_RE = re.compile(r"saved ([\d,]+)")
_OPENED_RE = re.compile(r"opened ([\d,]+)")
_VARIANTS_RE = re.compile(r"across ([\d,]+)")
_LOAD_LINK_RE = re.compile(r'class="load" href="([^"]+)"')


def parse_builds_page(page_html: str) -> dict[str, Any]:
    """The page's activity window and its top-5 rows in page order.

    Returns {"window", "window_build", "top"}; each row has exactly the keys
    rank, name, points, shared_total, saved_total, opened_total, variants, code.
    """
    window = _WINDOW_RE.search(page_html)
    top_list = _TOP_LIST_RE.search(page_html)
    rows_html = top_list.group(0) if top_list else ""
    return {
        "window": window.group(0) if window else None,
        "window_build": window.group(1) if window else None,
        "top": [_parse_row(row_html) for row_html in _ROW_RE.findall(rows_html)],
    }


def _parse_row(row_html: str) -> dict[str, Any]:
    text = html.unescape(re.sub("<[^>]+>", "", row_html))
    after_name = row_html.split("</h3>", 1)[1]
    return {
        "rank": int(_RANK_RE.search(row_html).group(1)),
        "name": html.unescape(re.sub("<[^>]+>", "", _NAME_RE.search(row_html).group(1))).strip(),
        "points": [int(digit) for digit in _POINTS_RE.findall(after_name)],
        "shared_total": _count(_SHARED_RE.search(text)),
        "saved_total": _count(_SAVED_RE.search(text)),
        "opened_total": _count(_OPENED_RE.search(text)),
        "variants": _count(_VARIANTS_RE.search(text)),
        "code": _LOAD_LINK_RE.search(row_html).group(1).split("/60/")[-1],
    }


def _count(match: re.Match[str]) -> int:
    return int(match.group(1).replace(",", ""))


def decode_build(code: str, export: dict[str, Any]) -> dict[str, int]:
    """A build code as {talent name: rank}, ranks above 0 only.

    The code is the three trees' digit strings joined by "-" plus a trailing
    segment (ignored): tree t's digit i is the rank of
    export["talents"]["trees"][t]["talents"][i], an empty segment takes none.
    """
    segments = code.split("-")
    final: dict[str, int] = {}
    for tree_index, tree in enumerate(export["talents"]["trees"]):
        segment = segments[tree_index] if tree_index < len(segments) else ""
        for digit_index, digit in enumerate(segment):
            rank = int(digit)
            if rank and digit_index < len(tree["talents"]):
                final[tree["talents"][digit_index]["name"]] = rank
    return final


def popular_builds(page_html: str, export: dict[str, Any]) -> list[dict[str, Any]]:
    """The page's top-5 rows, each with one more key: "final", the decoded code."""
    rows = parse_builds_page(page_html)["top"]
    return [dict(row, final=decode_build(row["code"], export)) for row in rows]


# ---- snapshots (#460): each class's builds page and export, saved gzipped and immutable ----

BASE_URL = "https://talentsforever.com"
CLASSES = ("druid", "hunter", "mage", "paladin", "priest", "rogue", "shaman", "warlock", "warrior")


def _digest(folder: Path) -> str:
    sha = hashlib.sha256()
    for path in sorted(folder.glob("*.gz")):
        sha.update(gzip.decompress(path.read_bytes()))
    return sha.hexdigest()


def fetch(*, http_get: Callable[[str], str], raw_dir: Path, classes: Sequence[str] = CLASSES, delay: float = 1.5,
          sleep: Callable[[float], None] = time.sleep) -> Path:
    """Each class's /<class>/builds page and /export/<class>.json, saved gzipped under `raw_dir` (named YYYYMMDD).
    A saved snapshot is immutable: when its manifest exists nothing is fetched. Returns the manifest's path."""
    manifest_path = raw_dir / "manifest.json"
    if manifest_path.exists():
        return manifest_path
    files: dict[str, str] = {}
    for n, class_slug in enumerate(classes):
        if n:
            sleep(delay)
        files[f"builds-{class_slug}.html"] = http_get(f"{BASE_URL}/{class_slug}/builds")
        sleep(delay)
        files[f"export-{class_slug}.json"] = http_get(f"{BASE_URL}/export/{class_slug}.json")
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (raw_dir / f"{name}.gz").write_bytes(gzip.compress(text.encode("utf-8"), mtime=0))
    name = raw_dir.name
    manifest_path.write_text(json.dumps({
        "source": SOURCE, "url": BASE_URL, "captured": f"{name[:4]}-{name[4:6]}-{name[6:]}", "classes": list(classes),
        "files": len(files), "sha256": _digest(raw_dir), "license": "CC BY 4.0",
    }, indent=1) + "\n", encoding="utf-8", newline="\n")
    return manifest_path


def load_snapshot(folder: Path) -> dict[str, tuple[str, dict[str, Any]]]:
    """A saved snapshot as {class: (builds page, export)}; refuses pages edited since they were saved."""
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if _digest(folder) != manifest["sha256"]:
        raise ValueError(f"{folder}: pages changed since the snapshot was saved")
    read = lambda name: gzip.decompress((folder / f"{name}.gz").read_bytes()).decode("utf-8")
    return {c: (read(f"builds-{c}.html"), json.loads(read(f"export-{c}.json"))) for c in manifest["classes"]}


def latest_snapshot(root: Path) -> Path | None:
    """The newest saved snapshot folder under `root` (YYYYMMDD names), or None."""
    folders = sorted(p for p in root.glob("[0-9]" * 8) if (p / "manifest.json").exists())
    return folders[-1] if folders else None
