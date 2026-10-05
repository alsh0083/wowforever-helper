"""Give each pytest run its own temp dir under .pytest-tmp.

Local agents run inside a sandbox that can create but not delete pytest's temp files, so reusing one
basetemp fails on the next run's cleanup. A fresh subdirectory per run needs no cleanup."""

import os

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if config.option.basetemp:
        parent = str(config.option.basetemp)
        try:
            os.makedirs(parent, exist_ok=True)   # pytest creates only the last path segment
        except OSError:
            # some sandboxes can't create it; fall back to pytest's default temp location
            config.option.basetemp = None
            return
        config.option.basetemp = os.path.join(parent, f"run-{os.getpid()}")
