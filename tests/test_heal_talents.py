"""Druid healing talents in self-healing (#276).

Talents that name a heal change its cast time and mana cost; Gift of Nature (new effect kind
`healing_pct`) multiplies all healing. Moonglow cuts only *damaging* spells' cost, so heals skip
school-wide effects: only effects naming the heal by name, plus `healing_pct`, apply.

Rank texts (Forever): Naturalist -0.1 s Healing Touch cast per rank; Gift of Nature +2% healing per
rank; Tranquil Spirit -2% Healing Touch and Tranquility mana cost per rank.

Rows: level 60 caster 312 spell power, 5030 mana; level 30 caster 93 spell power, 2330 mana.
Healing Touch r11 averages 2332 (840 mana, 3.5 s); r5 averages 546 (280 mana). Heal mana share 0.5.
  Restoration PvP 60 (Naturalist 5, Gift of Nature 2, Tranquil Spirit 1):
    (2332 + 312) x 1.04 = 2749.76 per 3.0 s = 916.59/s; cost 840 x 0.98 = 823.2;
    budget 5030 x 0.5 x 2749.76 / 823.2 = 8400.9.
    (Regrowth's direct part: 1110.2 x 1.04 = 1154.6 per 2.0 s = 577.3/s, lower.)
  Balance PvP 60 (Naturalist 5, Moonglow 3): 2644 per 3.0 s = 881.33/s; Moonglow doesn't apply,
    budget stays 5030 x 0.5 x 2644 / 840 = 7916.3.
  Restoration PvP 30 (leveling order: Naturalist 5, Gift of Nature 1, Moonglow 2):
    (546 + 93) x 1.02 = 651.78 per 3.0 s = 217.26/s; budget 2330 x 0.5 x 651.78 / 280 = 2711.9.
"""

import pytest

from wowforever.builds import load_builds
from wowforever.classes.druid import TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.pvp.class_pvp import heal_capacity
from wowforever.report import ranks_at
from wowforever.schema import Dataset, latest_dataset_path

CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("druid"), TALENT_EFFECTS, UNMODELED)
TABLE = stat_table("druid")
BUILDS = {b.id: b for b in load_builds(class_name="druid")}


def final(build_id):
    return BUILDS[build_id].final_ids(CLS)


def at_30(build_id):
    return ranks_at(BUILDS[build_id + "-leveling"].order_ids(CLS), 30, CLS)


def effects(name):
    return {e.kind: (e.values, e.applies_to) for e in next(t for t in CLS.talents if t.name == name).effects}


def test_healing_talents_parse_from_their_rank_texts():
    assert PROBLEMS == []
    assert effects("Naturalist")["cast_time"] == (pytest.approx((-0.1, -0.2, -0.3, -0.4, -0.5)), ("Healing Touch",))
    assert effects("Gift of Nature")["healing_pct"] == ((2.0, 4.0, 6.0, 8.0, 10.0), ("all",))
    assert effects("Tranquil Spirit")["mana_cost_pct"] == ((-2.0, -4.0, -6.0, -8.0, -10.0),
                                                           ("Healing Touch", "Tranquility"))


def test_restoration_heals_faster_stronger_and_cheaper():
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-restoration-pvp"))
    assert hps == pytest.approx(916.59, rel=1e-3) and budget == pytest.approx(8400.9, rel=1e-3)


def test_moonglow_does_not_cheapen_heals():
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-balance-pvp"))
    assert hps == pytest.approx(881.33, rel=1e-3) and budget == pytest.approx(7916.3, rel=1e-3)


def test_restoration_at_the_beta_cap():
    hps, budget = heal_capacity("druid", TABLE.at(30), CLS.spells, CLS, at_30("druid-restoration-pvp"))
    assert hps == pytest.approx(217.26, rel=1e-3) and budget == pytest.approx(2711.9, rel=1e-3)


def test_feral_takes_no_healing_talents():
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-feral"))
    assert hps == pytest.approx(666.29, rel=1e-3) and budget == pytest.approx(3734.0, rel=1e-3)
