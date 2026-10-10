"""Browser-tab icon (#246): the game's WoW Forever badge, inlined so the page stays offline."""

import base64
import json
from pathlib import Path

from wowforever.dashboard import FAVICON, render

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "dashboard" / "payload.json").read_text(encoding="utf-8"))
PNG = b"\x89PNG\r\n\x1a\nfakepng"


def test_render_puts_the_favicon_in_the_head_as_a_png_data_uri():
    html = render(PAYLOAD, {}, favicon=PNG)
    link = '<link rel="icon" type="image/png" href="data:image/png;base64,' + base64.b64encode(PNG).decode("ascii") + '">'
    assert html.count(link) == 1
    assert html.index("<title>") < html.index(link) < html.index("</head>")


def test_render_without_a_favicon_leaves_no_placeholder_or_link():
    html = render(PAYLOAD, {})
    assert "__FAVICON__" not in html and 'rel="icon"' not in html


def test_the_committed_favicon_is_a_64px_png():
    data = FAVICON.read_bytes()
    assert FAVICON == ROOT / "dashboard" / "favicon.png"
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert int.from_bytes(data[16:20], "big") == 64 and int.from_bytes(data[20:24], "big") == 64


def test_the_template_says_where_the_icon_comes_from():
    template = (ROOT / "dashboard" / "template.html").read_text(encoding="utf-8")
    assert "glues-wow-foreverlogo-infinity.blp" in template and "8363869" in template
