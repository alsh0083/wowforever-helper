"""Build descriptions (owner request, 2026-10-07): an "About this build" text for every build, from
the model's own data rather than hand-written prose, so it stays true as builds and engines change.

- Shape: the talent split, the focus, and when the build's key talents arrive on its order.
- Playstyle: what the engine's rotation actually does at level 60 (spells cast, builders and
  finishers, where the damage comes from).
- Strengths: the build's level-60 scenario scores against the class's other builds.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .schema import ClassData

SCENARIO_LABELS = {
    "questing": "questing speed", "dungeon": "dungeon damage", "raid": "raid damage", "aoe": "AoE pulls",
    "survival": "survivability", "control": "crowd control", "wpvp_melee": "duels against melee",
    "wpvp_melee_they_open": "duels where melee opens", "wpvp_caster": "duels against casters",
    "stealth_ambush": "surviving stealth openers", "battleground": "battlegrounds",
}
UNSCORED_NOTE = ("A healing or tanking build: the tool has no healing or threat model yet, so it has no "
                 "rotation or scores here, only the talent order.")


def _join(items: Sequence[str]) -> str:
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def shape(cls: ClassData, build: Mapping[str, Any], variant: str) -> str:
    """Talent split, focus and when the key talents arrive."""
    talents = {t.talent_id: t for t in cls.talents}
    trees = {t.tree_id: t.name for t in cls.trees}
    points: dict[str, int] = {}
    first: dict[int, int] = {}
    for i, tid in enumerate(build["order"]):
        points[trees[talents[tid].tree_id]] = points.get(trees[talents[tid].tree_id], 0) + 1
        first.setdefault(tid, cls.rules.first_talent_level + i)
    ranked = sorted(points.items(), key=lambda kv: -kv[1])
    main, rest = ranked[0], [f"{n} in {tree}" for tree, n in ranked[1:]]
    split = f"{main[1]} points in {main[0]}" + (f", with {_join(rest)}" if rest else "")
    focus = {"PvP": "Built for PvP.", "PvE": "Built for PvE."}.get(variant, "")
    # key talents: single-rank talents from the third row down (abilities and big passives: Mind Flay,
    # Blade Flurry, Seal of Command) and the build's deepest talent
    key = {tid for tid in first if talents[tid].max_rank == 1 and talents[tid].row >= 2}
    key.add(max(first, key=lambda tid: (talents[tid].row, -first[tid])))
    arrivals = [f"{talents[tid].name} at {first[tid]}" for tid in sorted(key, key=lambda tid: first[tid])][:6]
    out = f"{split}. {focus}".strip()
    if arrivals:
        out += f" On this order the key talents arrive as follows: {_join(arrivals)}."
    return out


def playstyle(class_name: str, facts: Mapping[str, Any]) -> str:
    """The engine's level-60 rotation in words."""
    if not facts:
        return ""
    kind = facts["kind"]
    if kind == "caster":
        parts = []
        if facts.get("dots"):
            parts.append(f"keeps {_join(facts['dots'])} up")
        if facts.get("cooldowns"):
            parts.append(f"uses {_join(facts['cooldowns'])} on cooldown")
        if facts.get("filler"):
            parts.append(f"fills with {facts['filler']}")
        return f"In the model's rotation it {_join(parts)}." if parts else ""
    if kind == "mage":
        bits = [f"levels with {facts['questing']}"] if facts.get("questing") else []
        if facts.get("raid") and facts.get("raid") != facts.get("questing"):
            bits.append(f"uses {facts['raid']} on long fights")
        if facts.get("aoe"):
            bits.append(f"pulls packs with {facts['aoe']}")
        if facts.get("pvp"):
            bits.append(f"duels with {facts['pvp']} as its main spell")
        return f"In the model it {_join(bits)}." if bits else ""
    split = facts.get("split") or {}
    share = _join([f"{label} {round(100 * v)}%" for label, v in split.items() if v >= 0.05])
    damage = f" Damage comes from {share}." if share else ""
    if kind == "rogue":
        return (f"Builds combo points with {facts['builder']} and spends them on finishers, keeping Slice and "
                f"Dice up.{damage}")
    if kind == "cat":
        return f"Fights in Cat Form, building combo points with {facts['builder']} for finishers.{damage}"
    if kind == "abilities":
        return f"In the model's rotation its priority is {_join(facts['abilities'])}.{damage}"
    if kind == "hunter":
        where = "at range with Auto Shot and its shots" if facts["mode"] == "ranged" else "in melee"
        pet_share = (facts.get("split") or {}).get("pet")
        pet = (f" alongside its pet, which does about {pet_share:.0%} of the damage" if facts.get("pet") and pet_share
               else " alongside its pet" if facts.get("pet") else " without a pet")
        return f"Fights {where}{pet}."
    if kind == "enhancement":
        return f"A melee shaman: auto-attacks and weapon procs carry it, with shocks and Stormstrike on top.{damage}"
    return ""


def strengths(build: Mapping[str, Any], best: Mapping[str, float]) -> str:
    """Level-60 scenario scores as a share of the class's best build in each."""
    shares = {}
    for scenario, by_level in (build.get("scores") or {}).items():
        cell = by_level.get("60") or by_level.get(60)
        if cell and cell.get("score") is not None and best.get(scenario) and scenario in SCENARIO_LABELS:
            shares[scenario] = cell["score"] / best[scenario]
    if len(shares) < 2:
        return ""
    ranked = sorted(shares.items(), key=lambda kv: -kv[1])
    if ranked[-1][1] >= 0.95:
        return (f"At level 60 it scores at or near the top of the class in {_join([SCENARIO_LABELS[s] for s, _ in ranked])}.")
    top = [f"{SCENARIO_LABELS[s]} ({v:.0%})" for s, v in ranked[:2]]
    low = ranked[-1]
    return (f"Against the class's best build in each scenario at level 60 it is strongest at {_join(top)}, and "
            f"weakest at {SCENARIO_LABELS[low[0]]} ({low[1]:.0%}).")


def class_best(builds: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    best: dict[str, float] = {}
    for b in builds:
        for scenario, by_level in (b.get("scores") or {}).items():
            cell = by_level.get("60") or by_level.get(60)
            if cell and isinstance(cell.get("score"), (int, float)):
                best[scenario] = max(best.get(scenario, 0.0), cell["score"])
    return best


def rotation_facts(class_name: str, cls: ClassData, ranks: Mapping[int, int], stats: Any,
                   scores: Mapping[str, Any]) -> dict[str, Any]:
    """What the class engine's rotation does at level 60 against a level-60 target."""
    from . import melee_scenarios as ms
    from .classes import class_module
    from .physical import Target

    if class_name == "mage":
        def cell(s: str) -> str | None:
            by_level = scores.get(s) or {}
            return (by_level.get("60") or by_level.get(60) or {}).get("spell")

        return {"kind": "mage", "questing": cell("questing"), "raid": cell("raid"), "aoe": cell("aoe"),
                "pvp": cell("wpvp_caster")}
    module = class_module(class_name)
    target = Target(0, 0)
    if isinstance(stats, ms.HybridStats):
        if ms.main_tree(cls, ranks) in module.MELEE_TREES:
            if class_name == "druid":
                from .classes.druid_rotation import cat_rotation

                r = cat_rotation(stats.melee, cls.spells, cls, ranks, target)
                return {"kind": "cat", "builder": r.builder,
                        "split": {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps}}
            from .classes.shaman_rotation import enhancement_rotation

            r = enhancement_rotation(stats.melee, cls.spells, cls, ranks, target)
            return {"kind": "enhancement", "split": {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps,
                                                     "spells and procs": r.spell_dps / r.dps}}
        stats = stats.caster
    if getattr(module, "ENGINE", None) == "spell":
        from .caster import caster_rotation

        r = caster_rotation(class_name, stats, cls.spells, cls, ranks, target)
        plan = module.ROTATION
        return {"kind": "caster", "dots": [s for s in r.spells if s in plan.get("dots", ())],
                "cooldowns": [s for s in r.spells if s in plan.get("cooldowns", ())],
                "filler": next((s for s in r.spells if s in plan.get("fillers", ())), None)}
    if class_name == "rogue":
        from .classes.rogue_rotation import rogue_rotation

        r = rogue_rotation(stats, cls.spells, cls, ranks, target)
        return {"kind": "rogue", "builder": r.builder,
                "split": {"auto-attacks": r.white_dps / r.dps, "abilities and poisons": r.yellow_dps / r.dps}}
    if class_name == "hunter":
        from .classes.hunter_rotation import hunter_rotation

        pet = ms._has_pet(cls, ranks)
        r = hunter_rotation(stats, cls.spells, cls, ranks, target, pet=pet)
        split = {"pet": r.pet_dps / r.dps} if pet and r.dps else {}
        return {"kind": "hunter", "mode": r.mode, "pet": pet, "split": split}
    if class_name in ("warrior", "paladin"):
        from .classes.paladin_rotation import paladin_rotation
        from .classes.warrior_rotation import warrior_rotation

        if class_name == "warrior":
            r = warrior_rotation(stats, cls.spells, cls, ranks, target)
            split = {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps}
        else:
            r = paladin_rotation(stats, cls.spells, cls, ranks, target)
            split = {"auto-attacks": r.white_dps / r.dps, "Holy damage": r.holy_dps / r.dps}
        return {"kind": "abilities", "abilities": list(r.abilities), "split": split}
    return {}


def add_descriptions(class_name: str, cls: ClassData, report: dict[str, Any], variants: Mapping[str, str],
                     stats_at_60: Any) -> None:
    """Sets `about` (a list of paragraphs) on every build in `report`."""
    best = class_best(report["builds"])
    for b in report["builds"]:
        paragraphs = [shape(cls, b, variants.get(b["id"], ""))]
        if not b.get("scores"):
            paragraphs.append(UNSCORED_NOTE)
        else:
            final = {}
            for tid in b["order"]:
                final[tid] = final.get(tid, 0) + 1
            try:
                facts = rotation_facts(class_name, cls, final, stats_at_60, b["scores"])
            except Exception:   # an engine that can't run this build at 60 just gets no playstyle line
                facts = {}
            paragraphs += [p for p in (playstyle(class_name, facts), strengths(b, best)) if p]
        if b.get("origin") == "model":
            paragraphs.append("A model build: the calculator's pick for this slot, not yet tried in game.")
        b["about"] = paragraphs
