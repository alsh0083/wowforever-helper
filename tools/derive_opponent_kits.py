"""Rewrite the rogue and hunter opponent kits' [at_60] health and DPS from the melee engine (#147).

Each kit's values come from its community build run at level 60 against a cloth target
(wowforever.pvp.kit_stats.engine_at_60). Run from the repo root:

    .venv/Scripts/python tools/derive_opponent_kits.py

Rewrites only the health and dps lines under [at_60] and the header comment that says health
and DPS are estimates; everything else stays byte-for-byte.
"""

from pathlib import Path

from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.pvp.kit_stats import DATASET, KIT_TREES, engine_at_60, kit_build
from wowforever.schema import Dataset

ROOT = Path(__file__).resolve().parents[1]
OPPONENTS = ROOT / "config" / "opponents"
HEADER_NOTE = "Health and DPS: level-60 values vs cloth from the damage engine (#147, #163)."


def rewrite(path: Path, kit_id: str) -> None:
    health, dps = engine_at_60(kit_id)
    class_name = kit_id.split("-", 1)[0]
    m = class_module(class_name)
    cls, _ = attach_effects(Dataset.load(DATASET).class_data(class_name), m.TALENT_EFFECTS, m.UNMODELED)
    note = f"# damage engine (#147, #163), build {kit_build(kit_id, cls).id}"
    lines = path.read_text(encoding="utf-8").split("\n")
    old_health = old_dps = None
    in_at_60 = False
    for i, line in enumerate(lines):
        if line.startswith("["):
            in_at_60 = line == "[at_60]"
            continue
        if in_at_60 and line.startswith("health = "):
            old_health = line.split("=", 1)[1].split("#")[0].strip()
            lines[i] = f"health = {round(health)}  {note}"
        elif in_at_60 and line.startswith("dps = "):
            old_dps = line.split("=", 1)[1].split("#")[0].strip()
            lines[i] = f"dps = {round(dps)}  {note}"
        elif "Health and DPS:" in line:
            lines[i] = line.split("Health and DPS:")[0] + HEADER_NOTE
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"{kit_id}: health {old_health} -> {round(health)}, dps {old_dps} -> {round(dps)}")


for kit_id in sorted(KIT_TREES):
    rewrite(OPPONENTS / f"{kit_id}.toml", kit_id)
