"""Offline dashboard: render the report payload into the template and cache talent icons."""

from __future__ import annotations

import base64
import html
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2] / "dashboard" / "template.html"
ICON_URL = "https://wowforevertalent.com/assets/icons/{}.jpg"


def render(payload: dict, icons: Mapping[str, bytes]) -> str:
    """Fill the template placeholders and return the complete HTML page."""
    template = TEMPLATE.read_text(encoding="utf-8")
    for placeholder in ("/*__PAYLOAD__*/null", "/*__ICONS__*/{}", "<!--__BUILD_BUTTONS__-->"):
        if placeholder not in template:
            raise ValueError(f"dashboard template is missing {placeholder}")
    icon_map = {
        name: "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
        for name, data in icons.items()
    }
    return (template.replace("/*__PAYLOAD__*/null", json.dumps(payload))
            .replace("/*__ICONS__*/{}", json.dumps(icon_map))
            .replace("<!--__BUILD_BUTTONS__-->", spec_matrix(payload)))


def build_buttons(builds: Sequence[Mapping]) -> str:
    """Switcher buttons from the payload, with each PvP/PvE pair side by side (PvP first)."""
    ordered = sorted(builds, key=lambda b: (b.get("pair") or b["id"], b.get("variant") != "PvP", b["id"]))
    return "\n".join(
        f'<button class="build-btn" data-build="{html.escape(b["id"])}">{html.escape(b["name"])}</button>'
        for b in ordered
    )


SCHOOL_VAR = {"Arcane": "--arcane", "Fire": "--fire", "Frost": "--frost"}
# Hybrid bars run from the route's foundation school to its finisher (Frost levels the Fire/Frost route).
HYBRID_ORDER = {"Fire/Frost": ("Frost", "Fire"), "Arcane/Fire": ("Arcane", "Fire")}


def _school_style(archetype: str) -> str:
    """Inline custom properties for the row's school bar: one colour, or a two-school blend."""
    if archetype in HYBRID_ORDER:
        a, b = HYBRID_ORDER[archetype]
    else:
        schools = [w for w in archetype.replace("/", " ").split() if w in SCHOOL_VAR]
        a = b = schools[0] if schools else "Arcane"
        if len(schools) > 1:
            b = schools[1]
    return f"--from:var({SCHOOL_VAR[a]});--to:var({SCHOOL_VAR[b]})"


def _gain(slot: Mapping) -> float | None:
    """Model pick's gain over the standard, or over its seed build when there is no standard."""
    pick = slot.get("model_pick_score")
    base = slot.get("standard_score")
    if base is None and slot.get("model_pick_seed"):
        cands = slot.get("candidates")
        base = cands.get(slot["model_pick_seed"]) if isinstance(cands, Mapping) else None
    if pick is None or not base:
        return None
    return (pick / base - 1) * 100


def _slot_cell(slot: Mapping, by_id: Mapping[str, Mapping]) -> str:
    e = html.escape
    cands = slot.get("candidates") if isinstance(slot.get("candidates"), Mapping) else {}
    parts = []

    def build_line(bid: str, caption: str, score: float | None) -> str:
        b = by_id.get(bid)
        if b is None:
            return ""
        yours = '<span class="tag">Yours</span>' if b.get("origin") == "hand" else ""
        num = f'<span class="score-num">{score:.2f}</span>' if score is not None else ""
        cap = f'<span class="caption">{caption}</span>' if caption else ""
        return (f'<div class="pick"><button class="build-btn" data-build="{e(bid)}">{e(b["name"])}</button>'
                f'{num}{yours}{cap}</div>')

    if slot.get("standard"):
        parts.append(build_line(slot["standard"], "Community standard", slot.get("standard_score")))
    else:
        parts.append('<p class="empty">No community standard yet</p>')
    for bid in slot.get("qualifying", []):
        if bid != slot.get("standard"):
            parts.append(build_line(bid, "Also qualifies" if slot.get("standard") else "Qualifies",
                                    cands.get(bid)))
    if slot.get("model_pick"):
        gain = _gain(slot)
        gain_txt = (f'{gain:+.1f}% vs {"standard" if slot.get("standard") else "its seed"}'
                    if gain is not None else f'scores {slot["model_pick_score"]:.2f}; no standard to compare against')
        seed = slot.get("model_pick_seed")
        label = f"Talent changes from {e(by_id[seed]['name'])}" if seed in by_id else "Full talent list"
        lines = "".join(f'<li>{e(c["talent"])} {c["from"]} → {c["to"]}</li>'
                        for c in slot.get("model_pick_changes", []))
        parts.append(f'<div class="model"><span class="model-label">Model pick, unproven</span> '
                     f'<span class="gain">{gain_txt}</span>'
                     f'<details><summary>{label}</summary><ul>{lines}</ul></details></div>')
    key = f'{slot["archetype"]}|{slot["focus"]}'
    return f'<div class="slot" data-slot="{e(key)}">{"".join(parts)}</div>'


def best_pair(payload: Mapping) -> tuple[tuple[str, float] | None, tuple[str, float] | None]:
    """Highest-scoring real build in each focus column, as (build id, score).

    Every slot in a column uses the same focus score, so builds compare across archetypes."""
    best: dict[str, tuple[str, float]] = {}
    for slot in payload.get("shortlist", []):
        cands = slot.get("candidates") if isinstance(slot.get("candidates"), Mapping) else {}
        for bid, score in cands.items():
            if bid in {b["id"] for b in payload["builds"]} and (
                    slot["focus"] not in best or score > best[slot["focus"]][1]):
                best[slot["focus"]] = (bid, score)
    return best.get("PvP"), best.get("PvE")


def _pair_line(payload: Mapping) -> str:
    """One line suggesting the dual-spec pair (from level 40) with the best score in each column."""
    pvp, pve = best_pair(payload)
    if not (pvp and pve):
        return ""
    names = {b["id"]: b["name"] for b in payload["builds"]}
    e = html.escape
    return (f'<p class="pair-line">Highest-scoring pair for dual spec from level 40: '
            f'<button class="build-btn" data-build="{e(pvp[0])}">{e(names[pvp[0]])}</button> '
            f'<span class="score-num">{pvp[1]:.2f}</span> with '
            f'<button class="build-btn" data-build="{e(pve[0])}">{e(names[pve[0]])}</button> '
            f'<span class="score-num">{pve[1]:.2f}</span>'
            f'<span class="caption">Scores only; community standing and playstyle still decide.</span></p>')


def spec_matrix(payload: Mapping) -> str:
    """The archetype x PvP/PvE matrix (#28): one row per archetype, cells in shortlist order.

    Builds that sit in no slot still get a button below the grid, so every build stays selectable."""
    e = html.escape
    by_id = {b["id"]: b for b in payload["builds"]}
    rows: dict[str, list[Mapping]] = {}
    for slot in payload.get("shortlist", []):
        rows.setdefault(slot["archetype"], []).append(slot)
    placed = {bid for s in payload.get("shortlist", []) for bid in [s.get("standard"), *s.get("qualifying", [])] if bid}
    out = ['<div class="matrix" role="table" aria-label="Builds by archetype and focus">',
           '<div class="mx-head" role="row"><span role="columnheader">Archetype</span>'
           '<span role="columnheader">PvP</span><span role="columnheader">PvE</span></div>']
    for archetype, slots in rows.items():
        cells = "".join(_slot_cell(s, by_id) for s in slots)
        out.append(f'<div class="mx-row" role="row"><div class="arch" data-archetype="{e(archetype)}" '
                   f'style="{_school_style(archetype)}">{e(archetype[:1].upper() + archetype[1:])}</div>{cells}</div>')
    out.append("</div>")
    out.append(_pair_line(payload))
    rest = [b for b in payload["builds"] if b["id"] not in placed]
    if rest:
        out.append('<div class="unplaced"><span class="caption">Not in a slot yet</span>'
                   + build_buttons(rest) + "</div>")
    return "\n".join(out)


def fetch_icons(names: Sequence[str], *, http_get_bytes, cache_dir: Path) -> dict[str, bytes]:
    """Icon name -> JPEG bytes for each unique non-empty name, reading `cache_dir` first."""
    icons: dict[str, bytes] = {}
    for name in dict.fromkeys(n for n in names if n):
        path = Path(cache_dir) / f"{name}.jpg"
        if path.is_file():
            icons[name] = path.read_bytes()
            continue
        data = http_get_bytes(ICON_URL.format(name))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        icons[name] = data
    return icons
