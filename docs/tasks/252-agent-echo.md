# Task #252: print the agent's final message on any console encoding

Make `tests/test_local_agent.py` pass without breaking the rest of the suite. Edit `tools/local_agent.py` only. Do not edit the tests.

## Why
With its output piped on Windows, `tools/local_agent.py` writes stdout as cp1252, and `print(last_message.read_text(...))` at the end of `main()` crashes on characters such as `→` (`UnicodeEncodeError: 'charmap' codec can't encode character '→'`).

## Change
1. Add a module-level function to `tools/local_agent.py`, above `main()`:
   ```python
   def echo(text: str, stream=None) -> None:
       """Write text and a newline to stream (default sys.stdout), replacing characters its encoding can't hold."""
   ```
   Encode with the stream's `encoding` (if it has none, e.g. `io.StringIO`, write the text unchanged) using `errors="replace"`, decode back, and write that plus `"\n"`. Look up `sys.stdout` at call time, not as a default argument.
2. In `main()`, replace `print(last_message.read_text(encoding="utf-8"))` with `echo(last_message.read_text(encoding="utf-8"))`.
3. Add `import sys` if it's missing. Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_local_agent.py` fails with `AttributeError: module 'local_agent' has no attribute 'echo'`. That's the expected failure. Install nothing and ask for no elevation. Write the edit with `tools/apply_patch.py` (see AGENTS.md). Don't run `tools/local_agent.py` itself, and don't run the full suite. Teardown errors about removing `.pytest-tmp` directories are a sandbox artifact: ignore them.

## Done when
`.venv/Scripts/python -m pytest tests/test_local_agent.py` passes.
