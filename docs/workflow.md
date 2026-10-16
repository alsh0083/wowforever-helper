# Local-model task workflow

Claude plans and audits; local models implement through `tools/local_agent.py`. Every task maps to a GitHub issue (see `AGENTS.md`).

## 1. Prepare (Claude)

1. Branch `<type>/<issue>-<slug>` from `main` (`feat/17-ev-engine`).
2. Write the tests first. For calculation code these are golden tests with hand-worked values in comments.
3. Write the task spec at `docs/tasks/<issue>-<slug>.md`:
   - **Goal:** one sentence, linking the issue
   - **Interface:** exact module paths, names and signatures the tests import
   - **Inputs:** fixture files to read (network access is never needed: Claude fetches raw data and saves it under `tests/fixtures/`)
   - **Constraints:** standard library unless stated, type hints, match surrounding style, files the agent may touch
   - **Done when:** the exact pytest command that must pass
   - **Steps:** which file and function to edit, in order, and what each change does: the formula, the data source, the names to use. Give tables of the exact inputs (rank text, data values) where the model would otherwise guess. Don't include the implementation: the model writes the code.
   - **Environment note:** `tools/local_agent.py` already sets `CODEX_EXE`; install nothing; which tests fail before the change; "don't re-check what this spec states"

   Since 2026-10-16 this tests-and-outline format is the default (#337: qwen3.8-27b wrote a 3-file change correctly in about 30 minutes; #341 in 11). Keep a task under about 150 changed lines. Put a reference diff in the spec only after a tests-and-outline run fails twice, and say so in the PR. qwen3-coder-30b breaks quoting in config edits (#342), so give config work to qwen3.8-27b too.
4. Commit tests and spec, push, and open a **draft** PR with `Refs #N`.

## 2. Run (local model)

```sh
.venv/Scripts/python tools/local_agent.py --model qwen3.8-27b --task docs/tasks/17-ev-engine.md
```

| Model | Use for |
|---|---|
| `qwen3.8-27b` | default for everything so far: it handles the Codex tooling on Windows far better |
| `qwen3-coder-30b` | only very small mechanical edits; on #7 it couldn't get files written and fell back to system Python |
| `gpt-oss-20b` | second opinion on a calculation or review |

Run tasks for the same model back to back; switching models reloads the GPU server. Logs go to `.agent-logs/` (gitignored).

## 3. Review (Claude)

- Run the full suite before merging: `.venv/Scripts/python -m pytest` (about 3.5 minutes). While iterating, `-m "not slow"` skips the full-report tests (about 10 s).
- Read the diff for: changed or deleted tests (reject), files outside the spec, hidden network calls, swallowed errors, copied magic numbers that belong in data or config.
- Stop a run that starts repairing the environment or touching files outside the repo; fix the environment yourself.
- Not done: re-run the agent with specific feedback appended to the spec, up to two times. After that Claude finishes the work and notes it in the PR.
- Done: commit as the agent's work with the model named in the PR body, mark the PR ready, squash-merge with `Closes #N`, and tick the issue's acceptance boxes.
