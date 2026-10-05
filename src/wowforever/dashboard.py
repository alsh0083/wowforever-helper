"""Offline dashboard: render the report payload into the template and cache talent icons."""

from __future__ import annotations

import base64
import html
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2] / "dashboard" / "template.html"
ICON_URL = "https://wowforevertalent.com/assets/icons/{}.jpg"


# Per-class look (#102): the in-game class color as the accent, three tree colors (main, dark
# card background, border), and a crest drawn in the mage crest's style.
CLASS_THEMES: dict[str, dict] = {
    "mage": {
        "label": "Mage", "accent": "#3FC7EB",
        "trees": {"Arcane": "arcane", "Fire": "fire", "Frost": "frost"},
        "crest": ('<svg viewBox="0 0 100 100" fill="none"><path d="M50 10v80M16 30l68 40M16 70l68-40M38 18l12 '
                  '12 12-12M38 82l12-12 12 12" stroke="#9bdeec" stroke-width="3"/><path d="M54 75C90 66 73 43 69 '
                  '39c1 12-9 16-11 8 4-20-13-29-13-29 8 21-9 24-11 38-2 12 6 21 20 19Z" fill="#db955b" '
                  'stroke="#ffe0a6" stroke-width="2"/></svg>'),
        "crest_bg": "linear-gradient(135deg,#123d53,#17212d 50%,#5c2b1f)",
    },
    "rogue": {
        "label": "Rogue", "accent": "#FFF468",
        "trees": {"Assassination": "assassination", "Combat": "combat", "Subtlety": "subtlety"},
        "crest": ('<svg viewBox="0 0 100 100" fill="none"><path d="M22 78L70 22l8 0 0 8-48 56z" fill="#c9ccd1" '
                  'stroke="#f4f0c8" stroke-width="2"/><path d="M78 78L30 22l-8 0 0 8 48 56z" fill="#a7abb3" '
                  'stroke="#f4f0c8" stroke-width="2"/><path d="M18 74l12 12M82 74L70 86" stroke="#fff468" '
                  'stroke-width="5" stroke-linecap="round"/><circle cx="50" cy="52" r="6" fill="#8fd16a"/></svg>'),
        "crest_bg": "linear-gradient(135deg,#25331c,#17191f 50%,#3a1c22)",
    },
    "hunter": {
        "label": "Hunter", "accent": "#AAD372",
        "trees": {"Beast Mastery": "beastmastery", "Marksmanship": "marksmanship", "Survival": "survival"},
        "crest": ('<svg viewBox="0 0 100 100" fill="none"><path d="M30 14c34 14 34 58 0 72" stroke="#c89a5b" '
                  'stroke-width="5" stroke-linecap="round"/><path d="M30 14v72" stroke="#e8e1c8" stroke-width="1.5"/>'
                  '<path d="M22 50h60" stroke="#e8e1c8" stroke-width="3"/><path d="M82 50l-10-7v14z" '
                  'fill="#aad372"/><path d="M22 50l-6-5M22 50l-6 5" stroke="#aad372" stroke-width="3"/></svg>'),
        "crest_bg": "linear-gradient(135deg,#2a3a1c,#191d17 50%,#3a2617)",
    },
}
# main, dark card background, border; mage trees keep their original card styles in the template
TREE_COLORS = {
    "assassination": ("#8fd16a", "#22371c", "#5f8f44"),
    "combat": ("#e0645a", "#3d1c1c", "#9a4a43"),
    "subtlety": ("#a68cf0", "#2a2342", "#7663b8"),
    "beastmastery": ("#d9774f", "#3b2219", "#9a5a3c"),
    "marksmanship": ("#e6c35c", "#3a321a", "#a08a43"),
    "survival": ("#5fb36b", "#1d3322", "#457f4d"),
}


def theme_css() -> str:
    """CSS for every class: accent per body[data-class], and talent-card styles per non-mage tree."""
    out = [":root{" + "".join(f"--{css}:{main};" for css, (main, _, _) in TREE_COLORS.items()) + "}"]
    for name, theme in CLASS_THEMES.items():
        out.append(f'body[data-class="{name}"]{{--accent:{theme["accent"]}}}'
                   f'body[data-class="{name}"] .crest{{background:{theme["crest_bg"]}}}')
    for css, (main, dark, border) in TREE_COLORS.items():
        out.append(
            f".{css} h2{{color:var(--{css})}}.{css} .talent.available{{border-color:{border}88}}"
            f".{css} .talent.complete{{background:linear-gradient(115deg,{dark}aa,#101923);border-color:{border}}}"
            f".{css} .icon,.icon.{css}-icon{{color:{main};background:radial-gradient(circle at 35% 25%,{border},"
            f"{dark} 75%);border-color:{border}}}"
            f".{css} .rank[aria-pressed=true]{{background:{dark};color:#fff;border-color:{main}}}"
            f".stat.{css} strong{{color:var(--{css})}}")
    return "".join(out)


def render(payload: dict | Sequence[dict], icons: Mapping[str, bytes]) -> str:
    """Fill the template placeholders and return the complete HTML page.

    `payload` is one class's report or a list of them (#102): the first is the page's default
    class, the others ride along for the class switcher."""
    payloads = [payload] if isinstance(payload, Mapping) else list(payload)
    first, others = payloads[0], payloads[1:]
    template = TEMPLATE.read_text(encoding="utf-8")
    for placeholder in ("/*__PAYLOAD__*/null", "/*__ICONS__*/{}", "<!--__BUILD_BUTTONS__-->",
                        "/*__OTHERS__*/{}", "/*__THEMES__*/{}", "/*__THEME_CSS__*/", "<!--__CLASS_TABS__-->"):
        if placeholder not in template:
            raise ValueError(f"dashboard template is missing {placeholder}")
    icon_map = {
        name: "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
        for name, data in icons.items()
    }
    names = [p.get("class", "mage") for p in payloads]
    matrices = "\n".join(f'<div class="class-matrix" data-class-matrix="{html.escape(n)}">{spec_matrix(p)}</div>'
                          for n, p in zip(names, payloads))
    tabs = "".join(f'<a class="class-tab" href="?class={html.escape(n)}" data-class-tab="{html.escape(n)}">'
                   f'{html.escape(CLASS_THEMES.get(n, {}).get("label", n.title()))}</a>' for n in names)
    themes = {n: {k: v for k, v in CLASS_THEMES[n].items() if k != "crest_bg"} for n in names if n in CLASS_THEMES}
    return (template.replace("/*__PAYLOAD__*/null", json.dumps(first))
            .replace("/*__OTHERS__*/{}", json.dumps({p.get("class", "mage"): p for p in others}))
            .replace("/*__THEMES__*/{}", json.dumps(themes))
            .replace("/*__THEME_CSS__*/", theme_css())
            .replace("<!--__CLASS_TABS__-->", tabs)
            .replace("/*__ICONS__*/{}", json.dumps(icon_map))
            .replace("<!--__BUILD_BUTTONS__-->", matrices))


def build_buttons(builds: Sequence[Mapping]) -> str:
    """Switcher buttons from the payload, with each PvP/PvE pair side by side (PvP first)."""
    ordered = sorted(builds, key=lambda b: (b.get("pair") or b["id"], b.get("variant") != "PvP", b["id"]))
    return "\n".join(
        f'<button class="build-btn" data-build="{html.escape(b["id"])}">{html.escape(b["name"])}</button>'
        for b in ordered
    )


SCHOOL_VAR = {tree: f"--{css}" for theme in CLASS_THEMES.values() for tree, css in theme["trees"].items()}
# Hybrid bars run from the route's foundation school to its finisher (Frost levels the Fire/Frost route).
HYBRID_ORDER = {"Fire/Frost": ("Frost", "Fire"), "Arcane/Fire": ("Arcane", "Fire")}


def _school_style(archetype: str) -> str:
    """Inline custom properties for the row's school bar: one colour, or a two-school blend."""
    if archetype in HYBRID_ORDER:
        a, b = HYBRID_ORDER[archetype]
    else:
        trees = [t for t in archetype.removeprefix("deep ").split("/") if t in SCHOOL_VAR]
        a = b = trees[0] if trees else "Arcane"
        if len(trees) > 1:
            b = trees[1]
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
        yours = ('<span class="tag">Yours</span>' if b.get("origin") == "hand"
                 else '<span class="tag">Model, unproven</span>' if b.get("origin") == "model" else "")
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
                   f'style="{_school_style(archetype)}">{e(archetype[:1].upper() + archetype[1:]).replace("/", "/<wbr>")}</div>{cells}</div>')
    out.append("</div>")
    out.append(_pair_line(payload))
    rest = [b for b in payload["builds"] if b["id"] not in placed]
    if rest:
        out.append('<div class="unplaced"><span class="caption">Other builds</span>'
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
