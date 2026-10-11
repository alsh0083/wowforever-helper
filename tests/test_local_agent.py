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
