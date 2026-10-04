"""Shared HTTP helper for source fetchers (personal-research traffic, stdlib only)."""

import urllib.request

USER_AGENT = "wowforever-helper/0.1 (personal research; github.com/alsh0083)"
TIMEOUT_SECONDS = 60.0


def http_get(url: str) -> str:
    """GET `url` and return the body as UTF-8 text; raises on non-200 or timeout."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise ValueError(f"GET {url} returned HTTP {response.status}")
        return response.read().decode("utf-8")
