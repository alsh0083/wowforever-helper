# Task #456 (part B3): skip skill-line spells a hotfix removed

Make `tests/test_spells.py` pass without breaking the rest of the fast suite
(`.venv/Scripts/python -m pytest -m "not slow"`). Do not edit the tests or anything under `tests/fixtures/`.

## Environment note
- `tools/local_agent.py` already sets `CODEX_EXE`; edit files with `tools/apply_patch.py` (see AGENTS.md).
- Install nothing. Edit only `src/wowforever/normalize_spells.py`.
- Before you start, `test_a_spell_removed_by_hotfix_is_skipped_but_a_missing_name_alone_is_an_error` fails; nothing else should.

## Why
The 30 Oct hotfixes removed Blessing of Salvation (spell 1038): its `Spell` and `SpellName` rows are gone, but the paladin's
`SkillLineAbility` row still points at it, so `class_spells` raises "no SpellName". A spell whose `Spell` row is also
missing was removed and is skipped. A name missing while the `Spell` row exists stays an error, and so does any
missing name when there is no `Spell` table.

## Step 1: in `class_spells`, replace
```python
    levels = _by_spell(tables["SpellLevels"])

    trainable: list[tuple[str, int, int]] = []
```
with
```python
    levels = _by_spell(tables["SpellLevels"])
    spell_rows = {int(row["ID"]) for row in tables["Spell"]} if "Spell" in tables else None

    trainable: list[tuple[str, int, int]] = []
```

## Step 2: replace
```python
        name = names.get(spell_id)
        if name is None:
            raise ValueError(f"skill line {row['SkillLine']}: no SpellName for spell {spell_id}")
```
with
```python
        name = names.get(spell_id)
        if name is None and spell_rows is not None and spell_id not in spell_rows:
            continue                    # removed by a hotfix (Spell and SpellName rows gone, skill line kept, #456)
        if name is None:
            raise ValueError(f"skill line {row['SkillLine']}: no SpellName for spell {spell_id}")
```

## Done when
- `tests/test_spells.py` passes; the fast suite has no other new failures. Only `src/wowforever/normalize_spells.py` changed.
