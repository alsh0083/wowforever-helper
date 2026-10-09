"""Fill empty spec-matrix slots from wowforevertalent.com's build catalog (owner request, 2026-10-05).

    .venv/Scripts/python tools/import_wft_builds.py            # report what it would write
    .venv/Scripts/python tools/import_wft_builds.py --write    # fetch plan pages and write TOMLs

For every deep-tree slot (archetype x PvP/PvE) with no community standard, it picks one level-60 plan
from the catalog (/builds/, robots allows all): verified final ranks first, then a verified point
order, then plans the site marks "needs review"; endgame guides before leveling plans. Each plan page
is fetched once, 1.5 s apart, and cached in data/cache/wft-builds/ (gitignored). Ranks are read from
the page's data, mapped to the client tree by talent name, and anything the client tree doesn't have
is dropped and reported. The TOML records the plan, its status and what was dropped.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
from pathlib import Path

from wowforever.classes import CLASSES
from wowforever.rules import points_available
from wowforever.schema import Dataset
from wowforever.sources.http import http_get
from wowforever.sources.wowforevertalent import decode_astro

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "wft-builds"
BASE = "https://wowforevertalent.com"
STATUS_RANK = {"verified-final": 0, "verified-order": 1, "needs-review": 2}


def props(page: str) -> dict | None:
    """The page's data props, or None for plan pages without a preview ("needs review" notes)."""
    m = re.search(r'<astro-island[^>]*props="([^"]*)"', page)
    if m is None:
        return None
    return {k: decode_astro(v) for k, v in json.loads(html.unescape(m.group(1))).items()}


def page(slug: str, *, fetch: bool) -> str | None:
    path = CACHE / f"{slug}.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    if not fetch:
        return None
    time.sleep(1.5)
    text = http_get(f"{BASE}/builds/{slug}/")
    path.write_text(text, encoding="utf-8", newline="\n")
    return text


def catalog() -> list[dict]:
    return props((CACHE / "index.html").read_text(encoding="utf-8"))["builds"]


def empty_slots() -> list[tuple[str, str, str]]:
    """(class, tree, focus) for deep slots without a community standard, from the reports."""
    out = []
    for c in CLASSES:
        report = json.loads((ROOT / "data" / ("report.json" if c == "mage" else f"report-{c}.json")).read_text(encoding="utf-8"))
        for slot in report["shortlist"]:
            if slot["archetype"].startswith("deep ") and not slot["standard"]:
                out.append((c, slot["archetype"][5:], slot["focus"]))
    return out


def candidates(plans: list[dict], cls: str, tree: str, focus: str) -> list[dict]:
    fits = [b for b in plans if b["classId"] == cls and b["specName"] == tree and b["levelMax"] == 60
            and focus.lower() in b["modes"]]
    return sorted(fits, key=lambda b: (STATUS_RANK.get(b["status"], 9), "endgame" not in b["stages"], b["slug"]))


def ranks_of(p: dict, cls_data) -> tuple[dict[str, int], list[str], list[str] | None]:
    """(final ranks by client talent name, dropped "name rank" notes, point order by name or None)."""
    trees = p["gameClass"]["trees"]
    names = {t.name: t for t in cls_data.talents}
    by_id = {t["id"]: t["name"] for tree in trees for t in tree["talents"]}
    seq = [by_id.get(s) for s in (p.get("sequence") or [])]
    published: dict[str, int] = {}
    if p.get("lockedRanks"):
        for tree, ranks in zip(trees, p["lockedRanks"]):
            for talent, rank in zip(tree["talents"], ranks):
                if rank > 0:
                    published[talent["name"]] = rank
    else:                                   # point-order plans publish only the sequence
        for name in seq:
            published[name] = published.get(name, 0) + 1
    final, dropped = {}, []
    for name, rank in published.items():
        t = names.get(name)
        if t is None or rank > t.max_rank:
            dropped.append(f"{name} {rank}")
        else:
            final[name] = rank
    order = seq if seq and not dropped and all(n in names for n in seq) else None
    return final, dropped, order


def toml_for(cls: str, tree: str, focus: str, plan: dict, final: dict, dropped: list[str], pair: str) -> tuple[str, str]:
    suffix = f"{tree.lower().replace(' ', '-')}-{focus.lower()}"
    build_id = f"{cls}-{suffix}"
    status = {"verified-final": "verified final ranks", "verified-order": "verified point order",
              "needs-review": "the site's 'needs review' (published points that didn't all match the tree)"}[plan["status"]]
    lines = [
        f"# {plan['listHeading']}: from wowforevertalent.com's build catalog (/builds/{plan['slug']}/),",
        f"# {status}, {plan['origin']} source, checked {plan.get('updatedAt', '')}. Not playtested.",
        "# Imported to fill an empty spec-matrix slot (owner request, 2026-10-05).",
    ]
    if dropped:
        lines.append(f"# Dropped (not on the client tree): {', '.join(dropped)}.")
    lines += ["", f'id = "{build_id}"', f'class = "{cls}"', f'name = "{tree} ({focus})"', f'pair = "{pair}"',
              f'variant = "{focus}"', 'origin = "community"', f'sources = ["wft_builds_{cls}"]',
              f'confidence = "{"medium" if plan["status"] != "needs-review" else "low"}"',
              f'summary = "{plan["summary"]} From the site\'s {plan["listHeading"]} plan."', "", "[final]"]
    lines += [f'"{n}" = {r}' for n, r in sorted(final.items())]
    return build_id, "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    from wowforever.schema import latest_dataset_path

    ds = Dataset.load(latest_dataset_path())
    plans = catalog()
    for cls, tree, focus in empty_slots():
        plan = data = None
        for option in candidates(plans, cls, tree, focus):
            text = page(option["slug"], fetch=args.write)
            if text is None:
                print(f"{cls} {tree} {focus}: would fetch {option['slug']} [{option['status']}]")
                break
            if (data := props(text)) is not None:
                plan = option
                break
        if plan is None:
            print(f"{cls} {tree} {focus}: no importable plan")
            continue
        cls_data = ds.class_data(cls)
        final, dropped, _ = ranks_of(data, cls_data)
        spent = sum(final.values())
        existing = {p.stem for p in (ROOT / "config" / "builds").glob(f"{cls}-*.toml")}
        pair = next((e for e in sorted(existing) if tree.lower().split()[0] in e), f"{cls}-{tree.lower().replace(' ', '-')}")
        build_id, toml = toml_for(cls, tree, focus, plan, final, dropped, pair)
        print(f"{cls} {tree} {focus}: {plan['slug']} [{plan['status']}] {spent} points, dropped {dropped}")
        if args.write and spent <= points_available(60, cls_data.rules):
            (ROOT / "config" / "builds" / f"{build_id}.toml").write_text(toml, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
