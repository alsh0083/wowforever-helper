"""Model builds for spec-matrix slots no community plan fills (owner request, 2026-10-05).

    .venv/Scripts/python tools/derive_slot_builds.py

Run after tools/import_wft_builds.py. For a slot whose report already has a model pick, the pick is
written as a build. Otherwise a seed (another build of the same tree, or a popular build with
off-tree talents removed) is topped up to 51 points one point at a time and hill-climbed under the
slot's focus score, staying in the slot's tree. Every build written here is labeled as a model build.
"""

from __future__ import annotations

import json
from pathlib import Path

from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.consensus import Consensus
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import pve_score, stat_table
from wowforever.pvp.class_pvp import pvp_score
from wowforever.pvp.duel import load_kits
from wowforever.rules import check_build, points_available
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.shortlist import improve

ROOT = Path(__file__).resolve().parents[1]
DS = Dataset.load(latest_dataset_path())

# Slots with no build of the other focus to start from: seed from a popular build instead,
# (class, tree, focus) -> ("popular", popularity rank, [site-only talents to drop])
SEEDED = {
    # Furious Precision and Lingering Rage were site-only until build 1.60.1.70291 added them (#239)
    ("warrior", "Fury", "PvE"): ("popular", 4, []),
    ("warrior", "Fury", "PvP"): ("popular", 4, []),
}


def write(cls_name: str, build_id: str, archetype: str, focus: str, ranks: dict[str, int], how: str) -> None:
    tree = archetype.removeprefix("deep ")
    pair = build_id.rsplit("-", 1)[0]
    lines = [f"# Model build for the empty {archetype} {focus} slot (owner request, 2026-10-05): {how}.",
             "# No community plan with talents exists for this slot yet; replace it when one does.", "",
             f'id = "{build_id}"', f'class = "{cls_name}"', f'name = "{tree} ({focus}, model)"', f'pair = "{pair}"',
             f'variant = "{focus}"', 'origin = "model"', 'sources = []', 'confidence = "low"',
             f'summary = "Model build for {tree} {focus}: {how}. Not a community standard."', "", "[final]"]
    lines += [f'"{n}" = {r}' for n, r in sorted(ranks.items())]
    (ROOT / "config" / "builds" / f"{build_id}.toml").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {build_id}: {sum(ranks.values())} points ({how})")


def slug(archetype: str) -> str:
    return archetype.removeprefix("deep ").lower().replace("/", "-").replace(" ", "-")


def run() -> int:
    """Fill every empty slot once; returns how many builds were written."""
    from wowforever.classes import CLASSES

    arch = Consensus.load().archetypes
    kits = load_kits()
    written = 0
    for c in CLASSES:
        report = json.loads((ROOT / "data" / ("report.json" if c == "mage" else f"report-{c}.json")).read_text(encoding="utf-8"))
        slots = {(s["archetype"], s["focus"]): s for s in report["shortlist"]}
        for (archetype, focus), slot in slots.items():
            if slot["standard"]:
                continue
            tree = archetype.removeprefix("deep ")
            build_id = f"{c}-{slug(archetype)}-{focus.lower()}"
            if slot.get("model_pick"):
                write(c, build_id, archetype, focus, slot["model_pick"], "the report's model pick for this slot")
                written += 1
                continue
            if c == "mage":
                print(f"{c} {archetype} {focus}: no model pick and no seed")
                continue
            m = class_module(c)
            cls, _ = attach_effects(DS.class_data(c), m.TALENT_EFFECTS, m.UNMODELED)
            stats = stat_table(c).at(60)
            fn = (lambda r, c=c, cls=cls, stats=stats: pve_score(c, stats, cls.spells, cls, r)) if focus == "PvE" else                  (lambda r, c=c, cls=cls, stats=stats: pvp_score(c, stats, cls.spells, cls, r, kits))
            other = slots.get((archetype, "PvE" if focus == "PvP" else "PvP"), {}).get("standard")
            special = SEEDED.get((c, tree, focus))
            if other:
                ranks = {b.id: b for b in load_builds(class_name=c)}[other].final_ids(cls)
                how = f"hill-climbed from {other} under the {focus} score"
            elif special:
                ranks, how = popular_seed(c, cls, fn, *special[1:], focus=focus)
            else:
                print(f"{c} {archetype} {focus}: no seed")
                continue
            ranks = top_up(cls, ranks, fn)
            best, _ = improve(cls, ranks, fn, archetype=archetype, deep=arch["deep"], hybrid=arch["hybrid"],
                              recognized=tuple(getattr(m, "HYBRIDS", ())), max_evals=400)
            names = {t.talent_id: t.name for t in cls.talents}
            write(c, build_id, archetype, focus, {names[t]: r for t, r in best.items() if r}, how)
            written += 1
    return written


def popular_seed(c, cls, fn, rank, drop, *, focus):
    pop = json.loads((ROOT / "data" / "popularity" / f"{c}.json").read_text(encoding="utf-8"))
    top = next(b for b in pop["top"] if b["rank"] == rank)
    wanted = {cls.talent_named(n).talent_id: r for n, r in top["final"].items() if n not in drop}
    # the site's tree is a build behind the client (#149): keep only the points the client tree
    # allows, spending them top row first
    ranks: dict[int, int] = {}
    for tid in sorted(wanted, key=lambda i: (cls.talent(i).row, i)):
        for _ in range(wanted[tid]):
            trial = dict(ranks)
            trial[tid] = trial.get(tid, 0) + 1
            if not check_build(cls, trial, None):
                ranks = trial
    dropped = f"{', '.join(drop)} (site-only talents) and " if drop else ""
    return ranks, (f"popular build #{rank} without {dropped}points the client "
                   f"tree doesn't allow, topped up and hill-climbed under the {focus} score")


def top_up(cls, ranks, fn):
    """Spend unspent points one at a time on the legal talent that scores best."""
    ranks = dict(ranks)
    while sum(ranks.values()) < points_available(60, cls.rules):
        options = []
        for t in cls.talents:
            if ranks.get(t.talent_id, 0) < t.max_rank:
                trial = dict(ranks)
                trial[t.talent_id] = trial.get(t.talent_id, 0) + 1
                if not check_build(cls, trial, None):
                    options.append((fn(trial), -t.talent_id, trial))
        if not options:
            break
        ranks = max(options, key=lambda o: o[:2])[2]
    return ranks


if __name__ == "__main__":
    print(f"wrote {run()} builds")
