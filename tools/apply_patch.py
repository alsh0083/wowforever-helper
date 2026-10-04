"""Apply a Codex-format patch read from stdin, for local-model agents on Windows.

Windows PowerShell 5.1 mangles embedded quotes in native-program arguments, so agents pipe the
patch here instead and this passes it to `codex --codex-run-as-apply-patch` as one argument.
Usage (PowerShell): see AGENTS.md.
"""

import os
import subprocess
import sys


def main() -> int:
    codex = os.environ.get("CODEX_EXE")
    if not codex:
        sys.exit("CODEX_EXE not set: run agents through tools/local_agent.py")
    patch = sys.stdin.buffer.read().decode("utf-8-sig").replace("\r\n", "\n").strip() + "\n"
    return subprocess.run([codex, "--codex-run-as-apply-patch", patch]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
