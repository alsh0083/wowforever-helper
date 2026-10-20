"""Level resistance for spell damage inside the melee engines (#435, after #409): Enhancement's shocks, Fire Nova and
Maelstrom bolt, rogue poisons, the hunter's Serpent Sting and Volley take the same average resist
(`level_resist_factor`, 0.94 at 60 against 63) when the `level_resistance` assumption is on."""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.calc.ev import level_resist_factor
from wowforever.classes import class_module
from wowforever.classes.hunter_rotation import hunter_rotation
from wowforever.classes.rogue_rotation import rogue_rotation
from wowforever.classes.shaman_rotation import enhancement_rotation
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import MeleeStatTable
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path

DS = Dataset.load(latest_dataset_path())
BOSS = Target(3, 3731)
OFF = Assumptions.load().with_values(level_resistance=False)


def loaded(name):
    m = class_module(name)
    cls, _ = attach_effects(DS.class_data(name), m.TALENT_EFFECTS, m.UNMODELED)
    return cls


@pytest.fixture
def resist_off(monkeypatch):
    def turn_off():
        monkeypatch.setattr(Assumptions, "load", classmethod(lambda cls, *a, **k: OFF))
    return turn_off


def test_factor(resist_off):
    assert level_resist_factor(60, 63) == pytest.approx(0.94)
    assert level_resist_factor(60, 60) == 1.0
    assert level_resist_factor(60, 63, 15) == pytest.approx(1 - 0.0225)
    resist_off()
    assert level_resist_factor(60, 63) == 1.0


def test_enhancement_spells(resist_off):
    cls = loaded("shaman")
    ranks = next(b for b in load_builds(class_name="shaman") if b.id == "shaman-enhancement").final_ids(cls)
    stats = MeleeStatTable.load("shaman_melee").at(60)
    on = enhancement_rotation(stats, cls.spells, cls, ranks, BOSS)
    resist_off()
    off = enhancement_rotation(stats, cls.spells, cls, ranks, BOSS)
    assert on.white_dps == pytest.approx(off.white_dps)
    assert on.shock_dps == pytest.approx(off.shock_dps * 0.94)
    assert on.maelstrom_dps == pytest.approx(off.maelstrom_dps * 0.94)      # 5/5: an instant, free bolt


def test_rogue_poisons(resist_off):
    cls = loaded("rogue")
    stats = MeleeStatTable.load("rogue").at(60)
    on = rogue_rotation(stats, cls.spells, cls, {}, BOSS)
    resist_off()
    off = rogue_rotation(stats, cls.spells, cls, {}, BOSS)
    assert off.poison_dps > 0
    assert on.poison_dps == pytest.approx(off.poison_dps * 0.94)
    assert on.white_dps == pytest.approx(off.white_dps)


def test_hunter_sting(resist_off):
    cls = loaded("hunter")
    stats = MeleeStatTable.load("hunter").at(60)
    on = hunter_rotation(stats, cls.spells, cls, {}, BOSS)
    resist_off()
    off = hunter_rotation(stats, cls.spells, cls, {}, BOSS)
    assert on.mode == off.mode == "ranged"
    assert on.ranged_dps < off.ranged_dps and on.auto_dps == pytest.approx(off.auto_dps)
