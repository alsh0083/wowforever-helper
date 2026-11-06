"""Talent rank text from the client's own tooltip (#466): the fallback when wowforevertalents.com links a talent but
serves no page for it (Call of Thunder, 4 Nov). Only a one-rank talent whose tooltip uses nothing but `$sN` (effect
N's base points) is rendered; anything else stays unread and the update stops as before."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_EFFECT = re.compile(r"\$s(\d)")


def render(description: str, base_points: Mapping[int, float]) -> str | None:
    """`description` with each `$sN` replaced by effect N's base points, or None if any token is left."""
    def value(match: re.Match[str]) -> str:
        points = base_points.get(int(match.group(1)) - 1)
        return match.group(0) if points is None else f"{abs(points):g}"

    text = _EFFECT.sub(value, description)
    return None if "$" in text else text


def talent_texts(tables: Mapping[str, Any], name: str) -> tuple[str, ...] | None:
    """The rank text of the one-rank trait talent `name`, from its spell's tooltip, or None."""
    ids = {int(r["ID"]) for r in tables["SpellName"] if r["Name_lang"] == name}
    spells = sorted(ids & {int(r["SpellID"]) for r in tables["TraitDefinition"]})
    if len(spells) != 1:
        return None
    spell_id = spells[0]
    description = next((r["Description_lang"] for r in tables["Spell"] if int(r["ID"]) == spell_id), "")
    points = {int(r["EffectIndex"]): float(r["EffectBasePointsF"]) for r in tables["SpellEffect"]
              if int(r["SpellID"]) == spell_id}
    text = render(description, points) if description else None
    return (text,) if text else None
