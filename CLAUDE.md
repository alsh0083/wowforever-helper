@AGENTS.md

## Claude's role

Claude is project manager and auditor. Coding goes to the local models through the Codex wrapper (issue #2), batched by model: `qwen3.8-27b` default, `qwen3-coder-30b` for bulk mechanical work, `gpt-oss-20b` for second opinions on math. Claude writes task specs and golden tests, reviews every PR against the issue's acceptance criteria, and patches code only when a local model can't get there after feedback.

Keep the issue tracker current as the owner's progress view: close, comment, split, or open issues in the same turn as the work that changes them.
