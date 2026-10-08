"""Leveling builds: the path to 60 of each endgame build (owner request and feedback, 2026-10-07).

    .venv/Scripts/python tools/derive_leveling_builds.py [--missing] [class ...]

For every endgame matrix slot with a main build, a leveling version of that build: the same playstyle and
talents, in a leveling order chosen for questing pace (PvP builds also lean toward their PvP talents,
so those come earlier: the mage's consensus core PvP talents, other classes' PvP-only talents), with up to
7 points at a time in talents the
endgame build doesn't take (Wand Specialization, Spirit Tap and the like) when they pay for questing.
Those points are respecced into the endgame build at 60. Writes config/builds/<endgame id>-leveling.toml
with the order; rerun the class reports afterwards.

(The first version picked any talents in a tree's direction; owner feedback: leveling builds should be the
endgame builds' own paths, a Fire/Frost mage levels as Fire/Frost, not a different build.)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from wowforever.builds import load_builds
from wowforever.classes import CLASSES, class_module
from wowforever.effects import attach_effects
from wowforever.optimizer import optimize_toward
from wowforever.rules import check_order, points_available
from wowforever.schema import Dataset

ROOT = Path(__file__).resolve().parents[1]
DS = Dataset.load(ROOT / "data" / "datasets" / "1.60.1.70205.json")
MAX_DETOUR = 7   # leveling-only points at a time (Spirit Tap 5 + Wand Specialization 2)
PVP_LEAN = 0.15  # PvP builds: up to +15% value once their PvP talents are taken (so they come earlier)


def pvp_talents(c: str, cls, target, report, endgame) -> dict[int, int]:
    """The target PvP build's PvP talents, at its ranks: for the mage the consensus core PvP talents,
    for other classes the ones its tree's PvE build doesn't take."""
    goal = target.final_ids(cls)
    if c == "mage":
        from wowforever.consensus import Consensus
        from wowforever.focus import pvp_core_talents

        core = {cls.talent_named(n).talent_id for n in pvp_core_talents(Consensus.load()) if any(x.name == n for x in cls.talents)}
        return {t: r for t, r in goal.items() if t in core}
    slot = next((s for s in report["shortlist"] if s.get("standard") == target.id), {})
    pve_slot = next((s for s in report["shortlist"] if s["archetype"] == slot.get("archetype") and s["focus"] == "PvE"), {})
    pve = endgame.get(pve_slot.get("standard") or "")
    pve_ids = pve.final_ids(cls) if pve else {}
    return {t: r for t, r in goal.items() if t not in pve_ids}


MAIN_TREE_LEAN = 0.25   # value x (1 + 0.25 x share of points in the build's main tree)


def questing_value(c: str, cls, target):
    """Questing kills/hour of a partial build at a level, played as the endgame build plays: the mage
    casts its primary spell, a hybrid keeps its melee or caster mode. Ties break toward the build at 60."""
    top = cls.rules.max_level
    if c == "mage":
        from wowforever.assumptions import Assumptions
        from wowforever.report import leveling_value
        from wowforever.stats import StatTable

        from wowforever.melee_scenarios import main_tree

        # model builds carry no primary spell: a Fire build levels on Fireball, a Frost one on Frostbolt
        primary = target.primary_spell or {"Fire": "Fireball", "Frost": "Frostbolt"}.get(main_tree(cls, target.final_ids(cls)), "")
        return leveling_value(cls, cls.spells, StatTable.load("mage"), Assumptions.load(), primary)
    from wowforever import melee_scenarios as ms

    table = ms.stat_table(c)
    melee = ms.main_tree(cls, target.final_ids(cls)) in getattr(class_module(c), "MELEE_TREES", ())

    def kills(ranks, level):
        return ms.questing(c, table.at(level), cls.spells, cls, ranks, melee=melee)

    return lambda ranks, level: kills(ranks, level) + 1e-3 * kills(ranks, top)


def with_main_tree(value, cls, target):
    """`value` leaning toward the build's main tree: early splash points cost more than they give, so the
    main tree comes first and splash talents only when they clearly pay (as guides level)."""
    from wowforever.melee_scenarios import main_tree

    main = next(t for t in cls.trees if t.name == main_tree(cls, target.final_ids(cls)))
    ids = set(main.talent_ids)

    def scored(ranks, level):
        spent = sum(ranks.values())
        share = sum(r for t, r in ranks.items() if t in ids) / spent if spent else 1.0
        return value(ranks, level) * (1 + MAIN_TREE_LEAN * share)
    return scored


def run(classes, missing_only: bool = False) -> int:
    written = 0
    for c in classes:
        m = class_module(c)
        cls, _ = attach_effects(DS.class_data(c), m.TALENT_EFFECTS, m.UNMODELED)
        report = json.loads((ROOT / "data" / ("report.json" if c == "mage" else f"report-{c}.json")).read_text(encoding="utf-8"))
        endgame = {b.id: b for b in load_builds(class_name=c) if b.mode == "endgame"}
        total = points_available(cls.rules.max_level, cls.rules)
        names = {t.talent_id: t.name for t in cls.talents}
        for slot in report["shortlist"]:
            target = endgame.get(slot.get("standard") or "")
            if target is None:
                continue
            build_id = f"{target.id}-leveling"
            path = ROOT / "config" / "builds" / f"{build_id}.toml"
            if missing_only and path.exists():
                continue
            value = with_main_tree(questing_value(c, cls, target), cls, target)
            lean = pvp_talents(c, cls, target, report, endgame) if target.variant == "PvP" else {}
            if lean:
                def scored(ranks, level, lean=lean):
                    taken = sum(min(ranks.get(t, 0), r) for t, r in lean.items())
                    return value(ranks, level) * (1 + PVP_LEAN * taken / sum(lean.values()))
            else:
                scored = value
            order = optimize_toward(cls, scored, target.final_ids(cls), max_detour=MAX_DETOUR, total=total)
            assert not check_order(cls, order), (c, build_id)
            name = target.name.replace(f"({target.variant}", f"({target.variant}, leveling", 1)
            lines = [f"# Leveling version of {target.id} (owner feedback, 2026-10-07): tools/derive_leveling_builds.py.",
                     "# Its talents in a questing-pace order, with up to 7 leveling-only points respecced at 60.", "",
                     f'id = "{build_id}"', f'class = "{c}"', f'name = "{name}"', f'pair = "{build_id}"',
                     f'variant = "{target.variant}"', 'mode = "leveling"', f'levels_into = "{target.id}"',
                     'origin = "model"', 'sources = []', 'confidence = "low"',
                     f'summary = "{target.name} for leveling: its talents in an order chosen for questing pace, with '
                     f'a few leveling talents along the way. Respec into {target.name} at 60."', "", "order = ["]
            lines += [f'  "{names[t]}",  # {cls.rules.first_talent_level + i}' for i, t in enumerate(order)]
            lines.append("]")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
            print(f"wrote {build_id}")
            written += 1
    return written


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--missing"]
    print(f"wrote {run(args or CLASSES, missing_only='--missing' in sys.argv)} leveling builds")
