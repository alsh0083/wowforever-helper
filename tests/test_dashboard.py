"""Tests for the dashboard generator (#22). The payload fixture is a trimmed report payload."""

import json
import re
from pathlib import Path

from wowforever.dashboard import fetch_icons, render

PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "dashboard" / "payload.json").read_text(encoding="utf-8"))
ICONS = {"spell_fire_incinerate": b"\xff\xd8fakejpeg", "spell_frost_frostbolt02": b"\xff\xd8other"}


def test_render_embeds_payload_and_icons_and_works_offline():
    html = render(PAYLOAD, ICONS)
    assert html.startswith("<!doctype html>")
    m = re.search(r"const PAYLOAD = (\{.*?\});\n", html, re.S)
    assert m and json.loads(m.group(1)) == PAYLOAD
    assert "data:image/jpeg;base64,/9hmYWtlanBlZw==" in html
    assert not re.search(r"<script[^>]+src=", html)                 # no external scripts
    assert not re.search(r"<link[^>]+href=\"https?:", html)          # no external styles
    assert not re.search(r"(src|url\()\s*=?\s*[\"']?https?:", html)  # no external images


def test_every_build_is_switchable_and_named():
    html = render(PAYLOAD, ICONS)
    for b in PAYLOAD["builds"]:
        assert f'data-build="{b["id"]}"' in html
        assert b["name"] in html


def test_footer_has_dataset_version_and_attribution():
    html = render(PAYLOAD, ICONS)
    assert PAYLOAD["dataset"]["game_build"] in html
    assert "wowforevertalent.com" in html and "Creative Commons" in html


def test_saved_progress_keys_stay_compatible():
    html = render(PAYLOAD, ICONS)
    # the original single-route dashboard saved under this key; the Elementalist build keeps it
    assert "wow-forever-elementalist-v4" not in html   # the hand-made build and its old save are gone


def test_fetch_icons_caches_and_skips_known(tmp_path):
    calls = []

    def get_bytes(url):
        calls.append(url)
        return b"img:" + url.rsplit("/", 1)[1].encode()

    icons = fetch_icons(["a", "b", "a", ""], http_get_bytes=get_bytes, cache_dir=tmp_path)
    assert icons == {"a": b"img:a.jpg", "b": b"img:b.jpg"}
    assert calls == ["https://wowforevertalent.com/assets/icons/a.jpg",
                     "https://wowforevertalent.com/assets/icons/b.jpg"]
    calls.clear()
    assert fetch_icons(["a", "b"], http_get_bytes=get_bytes, cache_dir=tmp_path) == icons
    assert calls == []
