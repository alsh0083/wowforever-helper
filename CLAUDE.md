@AGENTS.md

## Claude's role

Claude is project manager and auditor. Coding goes to the local models through the Codex wrapper (issue #2), batched by model: `qwen3.8-27b` default, `qwen3-coder-30b` for bulk mechanical work, `gpt-oss-20b` for second opinions on math. Claude writes task specs and golden tests, reviews every PR against the issue's acceptance criteria, and patches code only when a local model can't get there after feedback.

Since 2026-10-05 (docs/planning/2026-10-05.md), give local models small Python tasks pinned by tests and pure data/config work. Each task file carries an environment note: which failures are expected, install nothing, which file to edit first. If a run has no diff after about 30 minutes, stop it, implement the task directly, and say so in the PR. Never run pytest in a worktree while an agent is working in it.

Keep the issue tracker current as the owner's progress view: close, comment, split, or open issues in the same turn as the work that changes them.
