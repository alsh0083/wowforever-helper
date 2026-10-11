# Task #256: plain tmp_path directories inside agent runs

Make `tests/test_local_agent.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `tools/local_agent.py` and `conftest.py` (the repo root one).

## Why
Inside the agent sandbox, pytest creates its temp directories with `mkdir(mode=0o700)`, and the sandbox then refuses to list them: every `tmp_path` test errors with `PermissionError [WinError 5]`. A directory made with plain `mkdir()` works.

## Change
1. **`tools/local_agent.py`, `sandbox_env`:** also set `env["WOWFOREVER_AGENT"] = "1"`. Mention it in the docstring.
2. **`conftest.py`:** add `import re` and `from pathlib import Path`, then append:
   ```python
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
   ```
   Also add one sentence to the module docstring: inside agent runs, `tmp_path` comes from `agent_tmp_path` (#256).

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, the two new tests in `tests/test_local_agent.py` fail (`KeyError: 'WOWFOREVER_AGENT'`, and `conftest` has no `agent_tmp_path`). That's the expected failure. Your own session doesn't have `WOWFOREVER_AGENT` set yet, so `tmp_path` tests may still error with `PermissionError [WinError 5]` in setup. That's the bug this task fixes: ignore it. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md): `tools/local_agent.py` first, then `conftest.py`.

## Done when
`.venv/Scripts/python -m pytest tests/test_local_agent.py` passes (outside the sandbox, Claude runs it), and `.venv/Scripts/python -m pytest -m "not slow"` still passes.
