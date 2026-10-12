"""AoE pulls in every class's report and PvE score (#263).

melee_scenarios.aoe: seconds to clear a pack of `[aoe] pack` (3) same-level questing mobs
(config/scenarios.toml mob health) and how. Spell-engine classes and a hybrid's caster builds use
caster.aoe_pull (#260). Every other build clears the pack with its single-target rotation against the
questing mob's armor, 3 x mob health / DPS, until its AoE abilities are modeled (#262).

pve_score adds the AoE part as reference seconds / seconds (aoe_seconds 15, like the mage's
aoe_seconds_3): (questing / 100 + raid / 150 + dungeon / 150 + 15 / aoe) / 4.
Report rows: {"score": seconds rounded to 0.1, "unit": "seconds (3-mob pack)", "spell": ..., "lower_better": True}.
"""

import pytest

from wowforever import group
from wowforever import melee_scenarios as ms
from wowforever.builds import load_builds
from wowforever.caster import aoe_pull
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.physical import Target
from wowforever.scenarios import _anchor_at, default_params
from wowforever.schema import Dataset, latest_dataset_path

DATASET = Dataset.load(latest_dataset_path())
MOB_60 = default_params("aoe", 60).mob_hp


def setup(class_name, build_id):
    module = class_module(class_name)
    cls, _ = attach_effects(DATASET.class_data(class_name), module.TALENT_EFFECTS, module.UNMODELED)
    ranks = {b.id: b for b in load_builds(class_name=class_name)}[build_id].final_ids(cls)
    return cls, ranks, ms.stat_table(class_name).at(60)


def test_casters_use_their_aoe_spells():
    cls, ranks, stats = setup("warlock", "warlock-destruction-pve")
    pull = aoe_pull("warlock", stats, cls.spells, cls, ranks, 3, MOB_60)
    assert ms.aoe("warlock", stats, cls.spells, cls, ranks) == (pytest.approx(pull.seconds), pull.spell)
    assert pull.spell != "single target"


def test_melee_clears_the_pack_one_mob_at_a_time():
    cls, ranks, stats = setup("paladin", "paladin-retribution")   # paladin AoE is a later slice of #262
    armor = _anchor_at(ms._config()["questing"]["anchors"], 60)[0]
    dps = ms.rotation_output("paladin", stats, cls.spells, cls, ranks, Target(0, armor)).dps
    assert ms.aoe("paladin", stats, cls.spells, cls, ranks) == (pytest.approx(3 * MOB_60 / dps), "single target")


def test_hybrids_follow_their_tree():
    cls, ranks, stats = setup("druid", "druid-balance")
    pull = aoe_pull("druid", stats.caster, cls.spells, cls, ranks, 3, MOB_60)
    assert ms.aoe("druid", stats, cls.spells, cls, ranks) == (pytest.approx(pull.seconds), "Hurricane")
    cls, ranks, stats = setup("druid", "druid-feral")
    assert ms.aoe("druid", stats, cls.spells, cls, ranks)[1] == "single target"


def test_pve_score_adds_aoe_pulls_as_a_fourth_part():
    cls, ranks, stats = setup("warlock", "warlock-destruction-pve")
    expected = (ms.questing("warlock", stats, cls.spells, cls, ranks) / 100
                + ms.raid("warlock", stats, cls.spells, cls, ranks) / 150
                + group.typical_dungeon_dps("warlock", stats, cls, ranks) / 150
                + 15 / ms.aoe("warlock", stats, cls.spells, cls, ranks)[0]) / 4
    assert ms.pve_score("warlock", stats, cls.spells, cls, ranks) == pytest.approx(expected)
