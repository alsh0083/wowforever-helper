# Task #342: Feral Charge in the druid's PvP controls

Make `tests/test_feral_charge.py` pass. Edit only `config/pvp_self.toml`. Do not edit the tests.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Before you start, `test_feral_charge_roots_and_interrupts` fails and the other test passes.
- Don't re-check things this spec states.

## The change
In the `[druid]` table's `controls = [...]` list there is one entry, Entangling Roots. Add two
entries after it, in the same inline-table style the hunter's controls use (`requires = "..."`):

- name `"Feral Charge"`, kind `"root"`, duration `4.0`, cooldown `15`, requires `"Feral Charge"`
- name `"Feral Charge"`, kind `"interrupt"`, duration `4.0`, cooldown `15`, requires `"Feral Charge"`

Put a comment line above them: `# Feral Charge (Bear): immobilizes and interrupts for 4 s, 15 s cooldown (#342); LOW confidence: needs Bear Form`.

## Done when
`.venv/Scripts/python -m pytest tests/test_feral_charge.py` passes (2 tests).
