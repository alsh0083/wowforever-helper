"""Parsed config TOML, cached for the life of the process (#254).

Config files don't change during a run, so a path is parsed once and never re-checked: on Windows,
resolving or stat-ing the path costs a third as much as parsing it. `clear()` forgets everything.
"""

import copy
import tomllib
from pathlib import Path
from typing import Any

_CACHE: dict[Path, dict[str, Any]] = {}


def _parsed(path: Path) -> dict[str, Any]:
    """The cached parse of `path`, parsing on first use only."""
    path = Path(path)
    parsed = _CACHE.get(path)
    if parsed is None:
        parsed = _CACHE[path] = tomllib.loads(path.read_text(encoding="utf-8"))
    return parsed


def load_toml(path: Path) -> dict[str, Any]:
    """`path` parsed as TOML, parsed on first use only; each caller gets a deep copy to change freely."""
    return copy.deepcopy(_parsed(path))


def load_section(path: Path, key: str) -> Any:
    """A deep copy of the top-level table `key` of `path` (KeyError when missing), without copying the rest."""
    return copy.deepcopy(_parsed(path)[key])


def clear() -> None:
    """Forget every cached file."""
    _CACHE.clear()
