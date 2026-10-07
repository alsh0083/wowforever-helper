"""Leveling builds: a model talent path to 60 per class, tree and focus (owner request, 2026-10-07).

    .venv/Scripts/python tools/derive_leveling_builds.py [--missing] [class ...]

Not tied to an endgame build: every point goes to the legal talent (or the first point of the shortest
path that unlocks one) with the best questing pace at that level, from any talent of the class, with
at most 5 points outside the tree before level 40 and 20 in all, so it levels as that tree and ends deep
in it (31+ points). The PvP version keeps
questing pace and leans toward the talents the tree's endgame PvP build relies on: the duel model fights
level-60 opponents, so it can't score a level-25 duel. Writes config/builds/<class>-<tree>-leveling-
<focus>.toml with the order; rerun the class reports afterwards.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from wowforever.builds import load_builds
from wowforever.classes import CLASSES, class_module
from wowforever.effects import attach_effects
from wowforever.optimizer import optimize_free_order
from wowforever.rules import check_order, points_available
from wowforever.schema import Dataset

ROOT = Path(__file__).resolve().parents[1]
DS = Dataset.load(ROOT / "data" / "datasets" / "1.60.1.70205.json")
MAX_OFF_TREE = 20
EARLY_OFF_TREE, EARLY_POINTS = 5, 31   # at most 5 points outside the tree before level 40
PVP_LEAN = 0.15   # up to +15% value for spending every point on the endgame PvP build's talents


def questing_value(c: str, cls):
    """Questing kills/hour of a partial build at a level (ties break toward the build at 60)."""
    top = cls.rules.max_level
    if c == "mage":
        from wowforever.report import leveling_value
        from wowforever.assumptions import Assumptions
        from wowforever.stats import StatTable

        return leveling_value(cls, cls.spells, StatTable.load("mage"), Assumptions.load())
    from wowforever import melee_scenarios as ms

    table = ms.stat_table(c)

    def kills(ranks, level):
        return ms.questing(c, table.at(level), cls.spells, cls, ranks)

    return lambda ranks, level: kills(ranks, level) + 1e-3 * kills(ranks, top)


def slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def run(classes, missing_only: bool = False) -> int:
    written = 0
    for c in classes:
        m = class_module(c)
        cls, _ = attach_effects(DS.class_data(c), m.TALENT_EFFECTS, m.UNMODELED)
        report = json.loads((ROOT / "data" / ("report.json" if c == "mage" else f"report-{c}.json")).read_text(encoding="utf-8"))
        endgame = {b.id: b for b in load_builds(class_name=c) if b.mode == "endgame"}
        base = questing_value(c, cls)
        total = points_available(cls.rules.max_level, cls.rules)
        names = {t.talent_id: t.name for t in cls.talents}
        for tree in cls.trees:
            pvp_slot = next((s for s in report["shortlist"] if s["archetype"] == f"deep {tree.name}" and s["focus"] == "PvP"), None)
            pvp_build = endgame.get((pvp_slot or {}).get("standard") or "")
            pvp_talents = set(pvp_build.final_ids(cls)) if pvp_build else set()
            for focus in ("PvE", "PvP"):
                if missing_only and (ROOT / "config" / "builds" / f"{c}-{slug(tree.name)}-leveling-{focus.lower()}.toml").exists():
                    continue
                if focus == "PvP" and pvp_talents:
                    def value(ranks, level, base=base, pvp=frozenset(pvp_talents)):
                        spent = sum(ranks.values())
                        share = sum(r for t, r in ranks.items() if t in pvp) / spent if spent else 0.0
                        return base(ranks, level) * (1 + PVP_LEAN * share)
                    how = (f"questing pace at every level, leaning toward the talents of {pvp_build.name}, the tree's "
                           f"endgame PvP build")
                else:
                    value = base
                    how = "questing pace at every level"
                order = optimize_free_order(cls, value, main_tree=tree.tree_id, max_off_tree=MAX_OFF_TREE, total=total,
                                            early_off_tree=EARLY_OFF_TREE, early_points=EARLY_POINTS)
                assert not check_order(cls, order), (c, tree.name, focus)
                build_id = f"{c}-{slug(tree.name)}-leveling-{focus.lower()}"
                lines = [f"# Leveling build (owner request, 2026-10-07): tools/derive_leveling_builds.py, {how}.",
                         "# Any talent of the class: at most 5 points outside the tree before 40, 20 in all. Model-made, unproven.", "",
                         f'id = "{build_id}"', f'class = "{c}"', f'name = "{tree.name} leveling ({focus})"',
                         f'pair = "{build_id}"', f'variant = "{focus}"', 'mode = "leveling"', 'origin = "model"',
                         'sources = []', 'confidence = "low"',
                         f'summary = "A {tree.name} talent path for leveling to 60, chosen by the model for {how}. '
                         f'Not tied to an endgame build; respec at 60."', "", "order = ["]
                lines += [f'  "{names[t]}",  # {cls.rules.first_talent_level + i}' for i, t in enumerate(order)]
                lines.append("]")
                (ROOT / "config" / "builds" / f"{build_id}.toml").write_text("\n".join(lines) + "\n", encoding="utf-8",
                                                                             newline="\n")
                print(f"wrote {build_id}")
                written += 1
    return written


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--missing"]
    print(f"wrote {run(args or CLASSES, missing_only='--missing' in sys.argv)} leveling builds")
