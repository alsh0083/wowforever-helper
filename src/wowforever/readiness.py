"""Patch readiness (#366): what still breaks if the model moves to a saved dataset's build."""

from __future__ import annotations

from pathlib import Path

from wowforever import builds as builds_module
from wowforever import effects as effects_module
from wowforever import group
from wowforever import rules as rules_module
from wowforever.classes import CLASSES, class_module
from wowforever.normalize import read_tables
from wowforever.schema import Dataset

TABLES_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "wago"


def readiness(dataset_path: Path, *, tables_dir: Path | None = None) -> list[str]:
    """Open problems, one line each: effect rules that don't parse, builds naming unknown talents or illegal (final
    or order), and group buffs that don't resolve at 60. Empty when the model can move to this build."""
    ds = Dataset.load(dataset_path)
    problems: list[str] = []
    for name in CLASSES:
        cls = ds.class_data(name)
        module = class_module(name)
        _, report = effects_module.attach_effects(cls, module.TALENT_EFFECTS, module.UNMODELED)
        problems += [f"{name}: effect rule: {line}" for line in report]
        for b in builds_module.load_builds(class_name=name):
            unknown = b.unknown_talents(cls)
            if unknown:
                problems.append(f"{name}: build {b.id}: unknown talents {', '.join(unknown)}")
                continue
            lines = rules_module.check_build(cls, b.final_ids(cls), cls.rules.max_level)
            order = b.order_ids(cls)
            if order is not None:
                lines += [f"order: {line}" for line in rules_module.check_order(cls, order)]
            problems += [f"{name}: build {b.id}: {line}" for line in lines]
    tables = tables_dir or TABLES_DIR / ds.game_build
    if not tables.is_dir():
        problems.append(f"group buffs: client tables not cached at {tables.name}, not checked")
    else:
        resolved = group.build(read_tables(tables), group.talent_levels(ds, CLASSES), game_build=ds.game_build)
        for buff in resolved["buffs"]:
            if "60" not in (buff.get("by_level") or {}):
                problems.append(f"group buffs: {buff['id']} doesn't resolve at 60")
    return problems
