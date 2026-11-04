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


# ---- #463: a notice while the model reads an older build than the newest saved one ----

def test_pin_notice_is_empty_when_the_pin_is_current():
    from wowforever.dashboard import pin_notice

    assert pin_notice("1.60.1.70755", "1.60.1.70755", "#463") == ""
    assert pin_notice("1.60.1.70755", "1.60.1.70707", "#463") == ""


def test_pin_notice_names_both_builds_and_links_the_issue():
    from wowforever.dashboard import pin_notice

    notice = pin_notice("1.60.1.70425", "1.60.1.70755", "#463")
    assert notice == (
        '<div class="pin-notice" role="status">Scores are from game build 1.60.1.70425. Build 1.60.1.70755 '
        'is out, and moving the model to it is in progress: <a href="https://github.com/alsh0083/'
        'wowforever-helper/issues/463" target="_blank" rel="noopener noreferrer">#463</a>.</div>')
    # build numbers compare as numbers, not text
    assert pin_notice("1.60.1.9999", "1.60.1.10000", "#1") != ""


def test_render_puts_the_notice_under_the_header():
    from wowforever.dashboard import pin_notice

    notice = pin_notice("1.60.1.70425", "1.60.1.70755", "#463")
    html = render(PAYLOAD, ICONS, notice=notice)
    assert html.index(notice) > html.index("</header>")
    assert ".pin-notice{" in html
    assert "__NOTICE__" not in render(PAYLOAD, ICONS) and 'class="pin-notice"' not in render(PAYLOAD, ICONS)


def test_fetch_icons_leaves_out_an_icon_the_cdn_doesnt_have(tmp_path):
    # 1.60.1.70755 talents use icons the CDN lacks (ability_rogue_blackjack, inv_sword_32): the page draws those
    # talents without one instead of failing (#463)
    import urllib.error

    def get_bytes(url):
        if "missing" in url:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return b"jpeg:" + url.encode()

    icons = fetch_icons(["a", "missing", "b"], http_get_bytes=get_bytes, cache_dir=tmp_path)
    assert set(icons) == {"a", "b"} and not (tmp_path / "missing.jpg").exists()


def test_fetch_icons_still_fails_on_other_errors(tmp_path):
    import urllib.error

    import pytest

    def get_bytes(url):
        raise urllib.error.HTTPError(url, 503, "Unavailable", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        fetch_icons(["a"], http_get_bytes=get_bytes, cache_dir=tmp_path)
