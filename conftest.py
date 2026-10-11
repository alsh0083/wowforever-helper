"""Give each pytest run its own temp dir under .pytest-tmp.

Local agents run inside a sandbox that can create but not delete pytest's temp files, so reusing one
basetemp fails on the next run's cleanup. A fresh subdirectory per run needs no cleanup.
Inside agent runs, tmp_path comes from agent_tmp_path (#256)."""

import os
import re
from pathlib import Path

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


def agent_tmp_path(root: Path, nodeid: str, pid: int) -> Path:
    """A per-test temp dir under <root>/.pytest-tmp/agent-<pid>, created without a mode (#256):
    the agent sandbox denies listing directories pytest creates with mode 0o700."""
    path = Path(root) / ".pytest-tmp" / f"agent-{pid}" / re.sub(r"[^A-Za-z0-9_.-]", "_", nodeid)[-120:]
    path.mkdir(parents=True, exist_ok=True)
    return path


if os.environ.get("WOWFOREVER_AGENT") == "1":
    @pytest.fixture
    def tmp_path(request) -> Path:
        """Agent runs only (set by tools/local_agent.py): see agent_tmp_path."""
        return agent_tmp_path(request.config.rootpath, request.node.nodeid, os.getpid())
