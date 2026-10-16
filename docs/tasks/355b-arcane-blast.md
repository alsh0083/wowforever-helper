# Task #355, part B: Arcane Blast stacks in the mage rotation

Make `tests/test_70425_arcane_blast.py`, `tests/test_shared_raid.py` and `tests/test_one_pve_score.py` pass without
breaking the rest of the fast suite (`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests.

This task has no reference code to copy: you write the implementation.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing; the package and dataset are ready.
- Edit only `src/wowforever/classes/mage_rotation.py` and `src/wowforever/classes/mage.py`. Read only the
  functions named below. Don't re-check things this spec states, and **make the edits before running any tests**.
- Before you start, `tests/test_70425_arcane_blast.py` fails at import. The mage pins in
  `tests/test_dungeon_mana.py` may move after your change; Claude re-derives them.

## Why
On build 1.60.1.70425 the Arcane Blast talent's rank text says: "Each time you cast Arcane Blast, you gain 15% of your
Intellect as Spell Damage and the mana cost of Arcane Blast is increased by 175%. Effect stacks up to 4 times and
lasts 15 sec from time of initial application." Arcane Blast is a 1.5 s cast and costs 172 mana at 60.

Model: a 15 s buff window opens with n Arcane Blasts (0 ≤ n ≤ 4). The k-th of them (k = 0 … n-1) casts with k stacks:
+k × 15% of Intellect as spell damage, and a mana cost × (1 + 1.75 k). The filler then casts the rest of the window
with n stacks. There are 60 / 15 = 4 windows a minute. Which n is best depends on mana, so the mage tries every n
where it already picks its filler: the raid by its mana budget, questing by drinking, and dungeon pulls by a 60 s
pull's mana.

Spell damage on a spell is the same as adding `coefficient × bonus` to its `min_damage` and `max_damage`.

## Steps, in this order

### 1. `src/wowforever/classes/mage_rotation.py`
- Add `def arcane_blast_stacks(cls) -> tuple[float, float, int, float] | None:` above `rotation`. It reads
  `cls.talent_named("Arcane Blast").rank_text[-1]` (return None on `KeyError`) and matches "gain (A)% of your
  Intellect as Spell Damage and the mana cost of Arcane Blast is increased by (B)%. Effect stacks up to (C) times
  and lasts (D) sec". It returns `(A, B, C, D)` as `(float, float, int, float)`, or None when the text doesn't
  match. Give it a docstring.
- `rotation(...)`: add a keyword parameter `blast_stacks: int = 0`, and say in the docstring what it does.
- In `rotation`, just before `busy = sum(...)`:
  - `blast = best_rank(char.spells, "Arcane Blast", char.level)` when `blast_stacks > 0`, else None.
  - `stacks = arcane_blast_stacks(char.cls)` when `blast` is not None, else None.
  - `window_bonus = 0.0`.
  - When `stacks` is not None, with `(sp_pct, cost_pct, max_stacks, seconds) = stacks`:
    - `n = min(blast_stacks, max_stacks)` and `per_stack = sp_pct / 100 * stats.intellect`.
    - Take `blast_mods = mods_for(blast)`. For each k in `range(n)`, `add(...)` a copy of `blast` with
      `min_damage` and `max_damage` raised by `blast.coefficient * per_stack * k` and `mana_cost` set to
      `blast.mana_cost * (1 + cost_pct / 100 * k)`. Its count is `60 / seconds` a minute, its cast time is
      `effective_cast_time(blast, blast_mods)`, and its mods are `blast_mods`.
    - `rest = max(0, seconds - n * that cast time) / seconds`.
    - `boosted` is `filler` with both damages raised by `filler.coefficient * per_stack * n`.
    - `window_bonus = (ev_of(boosted, filler_mods) - ev_of(filler, filler_mods)) / cast * rest`.
- The line `dps = filler_dps` becomes `dps = filler_dps + window_bonus * (1.0 - busy / 60.0)`.

### 2. `src/wowforever/classes/mage.py`
- Add `def _blast_options(char) -> range:` above `_raid_output`. It returns `range(1)` (only 0) when
  `arcane_blast_stacks(char.cls)` is None or `best_rank(char.spells, "Arcane Blast", char.level)` is None, else
  `range(max_stacks + 1)`. Import inside the function.
- `_raid_output`: inside the filler loop, loop `for n in _blast_options(char):` and pass `blast_stacks=n` to
  `rotation`. Compute `fallback` once per filler, on the first n, as today's code does. Score each `(filler, n)`
  with `raid_dps` exactly as today and keep the best.
- `output` (the non-sustained path):
  - Compute `p = default_params("raid", stats.level)` and `income = combat_regen(char, p)` before the loop instead
    of after it.
  - Inside the filler loop, loop `for n in _blast_options(char):` with `blast_stacks=n`. The value stays `rot.dps`,
    or the drink-adjusted value when `drink_mana_per_second` is set.
  - With no drink and `n > 0`, the value is instead `dungeon_pull(Output(rot.dps, net, fallback), stats.mana,
    stats.level)`, where `net = rot.mana_per_second - (income - p.mana_per_second)` and
    `fallback = rot.dps * min(1.0, income / rot.mana_per_second)`. Import `dungeon_pull` from
    `wowforever.melee_scenarios`.
  - Put a one-line comment there saying Arcane Blast stacks are worth what a 60 s pull's mana pays for (#355).
  - The code after the loop stays as it is.

## Done when
- `tests/test_70425_arcane_blast.py` (5 tests), `tests/test_shared_raid.py` and `tests/test_one_pve_score.py` pass.
- The fast suite has no new failures apart from the mage dungeon pins.
