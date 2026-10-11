"""tools/local_agent.py prints the agent's final message on any console encoding (#252)."""

import importlib.util
import io
from pathlib import Path

spec = importlib.util.spec_from_file_location("local_agent", Path(__file__).resolve().parent.parent / "tools" / "local_agent.py")
local_agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_agent)


def test_echo_replaces_characters_the_console_cannot_encode():
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", newline="\n")   # a piped Windows console
    local_agent.echo("levels → config", stream)
    stream.flush()
    assert raw.getvalue() == b"levels ? config\n"


def test_echo_keeps_text_the_console_can_encode():
    stream = io.StringIO()
    local_agent.echo("levels → config", stream)
    assert stream.getvalue() == "levels → config\n"


def test_sandbox_env_marks_agent_runs(tmp_path):
    env = local_agent.sandbox_env(tmp_path / "codex.exe")
    assert env["WOWFOREVER_AGENT"] == "1"


def test_agent_tmp_path_is_a_plain_directory_per_test(tmp_path):
    import conftest
    first = conftest.agent_tmp_path(tmp_path, "tests/test_x.py::test_a[1-2]", pid=7)
    second = conftest.agent_tmp_path(tmp_path, "tests/test_y.py::test_a[1-2]", pid=7)
    assert first.is_dir() and second.is_dir() and first != second
    assert first.parent == tmp_path / ".pytest-tmp" / "agent-7"
    assert all(c.isalnum() or c in "_-." for c in first.name)
    assert conftest.agent_tmp_path(tmp_path, "tests/test_x.py::test_a[1-2]", pid=7) == first   # re-runs reuse it
