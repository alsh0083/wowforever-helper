"""Attach parsed per-rank numbers from talent rank texts as Effects (#51).

Class-agnostic: the per-class rule tables (modeled talents and their unmodeled peers) live in
`wowforever.classes` (e.g. `mage.TALENT_EFFECTS` / `mage.UNMODELED`).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import replace

from wowforever.classes import EffectRule
from wowforever.schema import ClassData, Effect, Talent


def attach_effects(cls: ClassData, rules: Mapping[str, tuple[EffectRule, ...]],
                   unmodeled: Mapping[str, str]) -> tuple[ClassData, list[str]]:
    """Return a copy of `cls` whose talents carry parsed Effects, plus a problem report."""
    report = _check_coverage(cls, rules, unmodeled)
    talents = [_with_effects(talent, rules, report) for talent in cls.talents]
    return replace(cls, talents=tuple(talents)), report


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
    if not effects:
        return talent
    return replace(talent, effects=tuple(effects))


def _parse_rule(talent: Talent, rule: EffectRule, report: list[str]) -> Effect | None:
    """One value per rank = `sign * float(match)`; None (plus a report line) on mismatch."""
    values: list[float] = []
    for rank, text in enumerate(talent.rank_text, start=1):
        match = re.search(rule.pattern, text)
        if match is None:
            report.append(f"{talent.name}: rank {rank} text didn't match {rule.kind} pattern")
            return None
        values.append(rule.sign * float(match.group(1)))
    return Effect(rule.kind, tuple(values), rule.applies_to)
