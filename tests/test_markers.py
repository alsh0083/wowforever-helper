"""The `slow` marker (#250): the full-report tests are skipped by the quick loop, `pytest -m "not slow"`."""

import importlib.util
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_slow_marker_is_registered():
    options = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]
    assert any(m.split(":")[0].strip() == "slow" for m in options["markers"])


def test_full_report_modules_are_marked_slow():
    for name in ("test_report", "test_melee_report"):
        spec = importlib.util.spec_from_file_location(name, ROOT / "tests" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        marks = module.pytestmark if isinstance(module.pytestmark, list) else [module.pytestmark]
        assert "slow" in [m.name for m in marks], name
