"""Give each pytest run its own temp dir under .pytest-tmp.

Local agents run inside a sandbox that can create but not delete pytest's temp files, so reusing one
basetemp fails on the next run's cleanup. A fresh subdirectory per run needs no cleanup."""

import os

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if config.option.basetemp:
        config.option.basetemp = os.path.join(str(config.option.basetemp), f"run-{os.getpid()}")
