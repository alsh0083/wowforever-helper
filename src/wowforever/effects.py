"""Attach parsed per-rank numbers from talent rank texts as Effects (#51).

Class-agnostic: the per-class rule tables (modeled talents and their unmodeled peers) live in
`wowforever.classes` (e.g. `mage.TALENT_EFFECTS` / `mage.UNMODELED`).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import replace

from wowforever.classes import EffectRule
from wowforever.schema import ClassData, Effect, Talent, talent_aliases


def attach_effects(cls: ClassData, rules: Mapping[str, tuple[EffectRule, ...]],
                   unmodeled: Mapping[str, str]) -> tuple[ClassData, list[str]]:
    """Return a copy of `cls` whose talents carry parsed Effects, plus a problem report."""
    rules, unmodeled = _by_dataset_name(cls, rules), _by_dataset_name(cls, unmodeled)
    report = _check_coverage(cls, rules, unmodeled)
    talents = [_with_effects(talent, rules, report) for talent in cls.talents]
    return replace(cls, talents=tuple(talents)), report


def _by_dataset_name(cls: ClassData, table: Mapping[str, object]) -> dict:
    """`table` keyed by the dataset's own talent names, so a rule written under a patch's new name
    (config/talent_renames.toml) still finds a dataset that has the old one, and vice versa."""
    names = {talent.name.lower(): talent.name for talent in cls.talents}
    out = {}
    for key, value in table.items():
        found = [names[a] for a in talent_aliases(key) if a in names]
        out[found[0] if len(found) == 1 else key] = value
    return out


def _check_coverage(cls: ClassData, rules: Mapping[str, tuple[EffectRule, ...]],
                    unmodeled: Mapping[str, str]) -> list[str]:
    """Names that must appear in exactly one of `rules` / `unmodeled`."""
    names = {talent.name for talent in cls.talents}
    report = [f"{name}: listed in both TALENT_EFFECTS and UNMODELED"
              for name in sorted(set(rules) & set(unmodeled))]
    report += [f"{name}: in neither TALENT_EFFECTS nor UNMODELED"
               for name in sorted(names - set(rules) - set(unmodeled))]
    report += [f"{name}: not a talent in the dataset"
               for name in sorted((set(rules) | set(unmodeled)) - names)]
    return report


def _with_effects(talent: Talent, rules: Mapping[str, tuple[EffectRule, ...]],
                  report: list[str]) -> Talent:
    """The talent with one Effect per modeled rule, or unchanged when none apply."""
    effects = []
    for rule in rules.get(talent.name, ()):
        effect = _parse_rule(talent, rule, report)
        if effect is not None:
            effects.append(effect)
    return replace(talent, effects=tuple(effects))  # also clears effects from older rules


def _parse_rule(talent: Talent, rule: EffectRule, report: list[str]) -> Effect | None:
    """One value per rank = `sign * float(match)`; None (plus a report line) on mismatch."""
    values: list[float] = []
    for rank, text in enumerate(talent.rank_text, start=1):
        match = re.search(rule.pattern, text)
        if match is None:
            report.append(f"{talent.name}: rank {rank} text didn't match {rule.kind} pattern")
            return None
        number = rule.combine(match) if rule.combine is not None else float(match.group(1))
        values.append(rule.sign * number)
    return Effect(rule.kind, tuple(values), rule.applies_to)
