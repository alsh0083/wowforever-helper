"""Offline dashboard: render the report payload into the template and cache talent icons."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2] / "dashboard" / "template.html"
ICON_URL = "https://wowforevertalent.com/assets/icons/{}.jpg"


def render(payload: dict, icons: Mapping[str, bytes]) -> str:
    """Fill the two template placeholders and return the complete HTML page."""
    template = TEMPLATE.read_text(encoding="utf-8")
    for placeholder in ("/*__PAYLOAD__*/null", "/*__ICONS__*/{}"):
        if placeholder not in template:
            raise ValueError(f"dashboard template is missing {placeholder}")
    icon_map = {
        name: "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
        for name, data in icons.items()
    }
    return template.replace("/*__PAYLOAD__*/null", json.dumps(payload)).replace(
        "/*__ICONS__*/{}", json.dumps(icon_map)
    )


def fetch_icons(names: Sequence[str], *, http_get_bytes, cache_dir: Path) -> dict[str, bytes]:
    """Icon name -> JPEG bytes for each unique non-empty name, reading `cache_dir` first."""
    icons: dict[str, bytes] = {}
    for name in dict.fromkeys(n for n in names if n):
        path = Path(cache_dir) / f"{name}.jpg"
        if path.is_file():
            icons[name] = path.read_bytes()
            continue
        data = http_get_bytes(ICON_URL.format(name))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        icons[name] = data
    return icons
