# wowforever-helper

Theorycrafting tools for WoW Forever: versioned talent/spell data → build legality → expected-value calculator → generated offline dashboard. Mage (Fire/Frost) first; everything outside a per-class module stays class-agnostic.

## GitHub issues are the project's memory

Issues on `alsh0083/wowforever-helper` are the single source of truth for what is planned, in progress, done, or broken. Milestones `v0` → `v1` → `later` order the work; `Depends on #N` lines order it within a milestone. Labels: one `area:*` per issue, plus `local-model` (implemented through Codex, reviewed by Claude), `claude` (design/audit done by Claude directly), and `needs-decision` (blocked on the owner).

For every piece of work:

1. **Start from an issue.** Pick an open issue whose dependencies are closed, or open one first. Read its acceptance criteria before writing code.
2. **Branch and PR per issue.** The PR body says `Closes #N`, the task spec, and which model did the work. Local-model tasks follow `docs/workflow.md` (spec format, running `tools/local_agent.py`, review rules).
3. **Log as you go.** Anything discovered that falls outside the current issue becomes its own issue: a bug (label `bug`), a next step, a changed assumption, a source-data change from an update check. Give it an area label and milestone and link it from the current issue or PR.
4. **Done means:** tests pass, every acceptance box ticked, PR merged, issue closed. If scope changed, edit the issue body so it describes what was actually built.
5. **Decisions the owner must make** go in an issue labelled `needs-decision`; work waits until it's answered.

`gh issue list -R alsh0083/wowforever-helper --milestone v0` shows the current frontier.

## Editing files as a local-model agent (Codex on Windows)

The shell `apply_patch` command mangles multi-line patches. Write the patch into a PowerShell here-string and call Codex directly:

```powershell
$patch = @'
*** Begin Patch
*** Add File: src/example.py
+print("hello")
*** End Patch
'@
& $env:CODEX_EXE --codex-run-as-apply-patch $patch
```

Use `*** Update File:` with `@@` hunks to edit and `*** Delete File: path` (no body lines) to delete. Run tests with `.venv/Scripts/python -m pytest`.

## Guardrails

- Every spell and talent value comes from Forever data. Classic/TBC values serve only as comparison and as consensus evidence for unchanged talents: Forever reworked a lot, mage AoE included.
- Calculation code is accepted only against tests written before the implementation, with hand-worked golden values.
- Fetch data only from sources whose robots.txt allows it (wago.tools, wowforevertalent.com). Wowhead disallows AI agents: read it only when the owner points to something there.
- wowforevertalent.com data is CC-BY: keep attribution in the README and dashboard footer.
- Update checks run when the owner asks. The project has no scheduled jobs or background services.
- Raw snapshots under `data/raw/` are immutable once committed; new data means a new snapshot.
- Unknown mechanics (Frostfire Bolt procs, etc.) are explicit toggles in `config/`, replaced by dated, patch-tagged in-game test results.
