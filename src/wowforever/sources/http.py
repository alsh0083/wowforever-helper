"""Shared HTTP helper for source fetchers (personal-research traffic, stdlib only)."""

from collections.abc import Mapping

import urllib.request

USER_AGENT = "wowforever-helper/0.1 (personal research; github.com/alsh0083)"
TIMEOUT_SECONDS = 60.0


def _get(url: str, extra_headers: Mapping[str, str]) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **extra_headers})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise ValueError(f"GET {url} returned HTTP {response.status}")
        return response.read()


def http_get_bytes(url: str) -> bytes:
    """GET `url` and return the raw body; raises on non-200 or timeout."""
    return _get(url, {})


def http_get(url: str) -> str:
    """GET `url` and return the body as UTF-8 text; raises on non-200 or timeout."""
    return http_get_bytes(url).decode("utf-8")


def http_get_with_headers(url: str, headers: Mapping[str, str]) -> str:
    """GET `url` with `headers` in addition to the User-Agent; returns the body as UTF-8 text."""
    return _get(url, headers).decode("utf-8")
