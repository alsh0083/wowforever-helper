"""Run a coding task on a local llama-swap model through the Codex CLI bundled with the Codex app.

Usage:
    python tools/local_agent.py --model qwen3.8-27b --task task.md
    python tools/local_agent.py --model qwen3-coder-30b < task.md

The user's ~/.codex/config.toml is ignored; the provider, model and sandbox are passed as
overrides so the Codex app's own settings stay untouched. Codex may write only inside the repo.
The Windows sandbox is "unelevated" (restricted token as the current user): the "elevated" mode runs
as a separate sandbox user that can't read Python under %LOCALAPPDATA%, so agents couldn't run tests.
WindowsApps is dropped from PATH so Codex uses System32 powershell.exe: the Store pwsh.exe alias there
fails about half the time under the sandbox token (CreateProcessAsUserW: access denied).
Each run is logged to .agent-logs/<timestamp>-<model>/ (gitignored): the task spec, the JSONL
event stream, and the agent's final message, which goes into the PR body.
"""

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LLAMA_SWAP = "http://192.168.1.215:8080/v1"
MODELS = {
    "qwen3.8-27b": "default coder",
    "qwen3-coder-30b": "bulk / mechanical work",
    "gpt-oss-20b": "second opinion",
}


def find_codex() -> Path:
    """Newest app-bundled codex.exe (its hash directory changes on app updates), else PATH."""
    bundled = Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI" / "Codex" / "bin"
    candidates = sorted(bundled.glob("*/codex.exe"), key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0]
    on_path = shutil.which("codex")
    if on_path:
        return Path(on_path)
    sys.exit("codex not found: install the Codex app or put the Codex CLI on PATH")


def sandbox_env(codex: Path) -> dict[str, str]:
    """Current environment minus WindowsApps on PATH (see module docstring), plus CODEX_EXE so the
    agent can call apply_patch directly (AGENTS.md has the recipe)."""
    env = dict(os.environ)
    env["CODEX_EXE"] = str(codex)
    env["PATH"] = os.pathsep.join(
        p for p in env.get("PATH", "").split(os.pathsep) if "windowsapps" not in p.lower()
    )
    return env


def build_command(codex: Path, model: str, last_message: Path) -> list[str]:
    return [
        str(codex), "exec",
        "--ignore-user-config",
        "--json",
        "-o", str(last_message),
        "-C", str(REPO),
        "-s", "workspace-write",
        "-m", model,
        "-c", 'windows.sandbox="unelevated"',
        "-c", 'model_provider="llamaswap"',
        "-c", f'model_providers.llamaswap={{name="llama-swap", base_url="{LLAMA_SWAP}", wire_api="responses"}}',
        "-",  # task spec on stdin
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="qwen3.8-27b", choices=MODELS)
    parser.add_argument("--task", type=Path, help="task spec file (default: stdin)")
    args = parser.parse_args()

    spec = args.task.read_text(encoding="utf-8") if args.task else sys.stdin.read()
    if not spec.strip():
        sys.exit("empty task spec")

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = REPO / ".agent-logs" / f"{stamp}-{args.model}"
    log_dir.mkdir(parents=True)
    (log_dir / "task.md").write_text(spec, encoding="utf-8")
    last_message = log_dir / "final.md"

    with open(log_dir / "events.jsonl", "w", encoding="utf-8") as events:
        codex = find_codex()
        result = subprocess.run(
            build_command(codex, args.model, last_message),
            input=spec, stdout=events, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            env=sandbox_env(codex),
        )

    print(f"log: {log_dir.relative_to(REPO)}  exit: {result.returncode}")
    if last_message.exists():
        print(last_message.read_text(encoding="utf-8"))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
