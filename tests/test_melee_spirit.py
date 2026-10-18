"""Spirit on the melee stat rows (#393, #399 part A): base Spirit plus gear Spirit, written as the last CSV column,
for the hunter's and paladin's mana regen talents."""

import csv
from pathlib import Path

from wowforever.melee_scenarios import MeleeStatTable
from wowforever.melee_stats import COLUMNS, MeleeStats

ROOT = Path(__file__).resolve().parents[1]


def test_meleestats_has_spirit_with_a_default():
    assert MeleeStats.__dataclass_fields__["spirit"].default == 0.0
    assert COLUMNS[-1] == "spirit"


def test_tables_carry_spirit():
    for name in ("rogue", "hunter", "warrior", "warrior_dw", "paladin", "druid_melee", "shaman_melee"):
        with open(ROOT / "config" / "stats" / f"{name}.csv", encoding="utf-8") as handle:
            assert next(csv.reader(handle))[-1] == "spirit", name
        with open(ROOT / "config" / "stats" / f"{name}_base.csv", encoding="utf-8") as handle:
            base60 = next(r for r in csv.DictReader(handle) if r["level"] == "60")
        assert MeleeStatTable.load(name).at(60).spirit >= float(base60["spirit"]), name


def test_a_table_without_the_column_reads_zero(tmp_path):
    src = ROOT / "config" / "stats" / "rogue.csv"
    rows = list(csv.reader(src.open(encoding="utf-8")))
    (tmp_path / "old.csv").write_text("\n".join(",".join(r[:-1]) for r in rows) + "\n", encoding="utf-8")
    assert MeleeStatTable.load("old", config_dir=tmp_path).at(60).spirit == 0.0
