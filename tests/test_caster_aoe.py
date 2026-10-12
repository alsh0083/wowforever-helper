"""AoE pulls for casters (#260, option 3 of #248): seconds to clear a pack of same-level mobs.

Each of the class's `aoe_spells` (config/casters.toml) goes out once per period = max(cast seconds,
cooldown), and the single-target rotation fills the rest of the time:
  rate = ev x hits / period + (1 - seconds / period) x single DPS;  seconds = pack x mob health / rate.
The rotation alone takes pack x mob health / single DPS; the fastest option wins.
hits = the pack size for spells that hit every mob; for a jumping spell (aoe_max_targets) the sum of
(1 - falloff)^k over min(pack, max targets) jumps; falloff is assumption `chain_jump_falloff_pct` (30).

Hand-worked (pack 3, 1000 health, single DPS 100: rotation alone 30 s):
  channel, every mob, 400 per target, 8 s: 1200 / 8 = 150/s, 20 s
  Chain Lightning-like, 300, 2 s cast, 6 s cooldown, 3 targets, 30%: hits 1 + 0.7 + 0.49 = 2.19;
    657 / 6 + (4/6) x 100 = 176.1667/s, 17.029328 s; with no falloff 900 / 6 + 66.667 = 216.667/s, 13.846154 s
  pack 2: hits 1.7, 85 + 66.667 = 151.667/s, 2000 / 151.667 = 13.186813 s
  pack 1: hits 1, 50 + 66.667 = 116.667/s, 8.571429 s
"""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.caster import aoe_pull, caster_rotation, chain_hits, pull_seconds
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import build_stats, stat_table
from wowforever.physical import Target
from wowforever.scenarios import default_params
from wowforever.schema import Dataset, latest_dataset_path

DATASET = Dataset.load(latest_dataset_path())


def test_jumping_spells_lose_damage_per_jump():
    assert chain_hits(1, 3, 30) == pytest.approx(1.0)
    assert chain_hits(2, 3, 30) == pytest.approx(1.7)
    assert chain_hits(3, 3, 30) == pytest.approx(2.19)
    assert chain_hits(5, 3, 30) == pytest.approx(2.19)
    assert chain_hits(3, 3, 0) == pytest.approx(3.0)
    assert chain_hits(3, 0, 30) == pytest.approx(3.0)   # 0 = hits every mob


def test_pull_seconds_mix_the_aoe_spell_into_the_rotation():
    assert pull_seconds(3, 1000, 100, 400, 8, 8, 3) == pytest.approx(20.0)
    assert pull_seconds(3, 1000, 100, 300, 2, 6, 2.19) == pytest.approx(17.029328, rel=1e-6)
    assert pull_seconds(3, 1000, 100, 300, 2, 6, 3.0) == pytest.approx(13.846154, rel=1e-6)
    assert pull_seconds(2, 1000, 100, 300, 2, 6, 1.7) == pytest.approx(13.186813, rel=1e-6)
    assert pull_seconds(1, 1000, 100, 300, 2, 6, 1.0) == pytest.approx(8.571429, rel=1e-6)


def pull(class_name, build_id, level=60, pack=3, **assumed):
    module = class_module(class_name)
    cls, problems = attach_effects(DATASET.class_data(class_name), module.TALENT_EFFECTS, module.UNMODELED)
    ranks = {b.id: b for b in load_builds(class_name=class_name)}[build_id].final_ids(cls)
    stats = build_stats(class_name, stat_table(class_name).at(level), cls, ranks)
    mob_hp = default_params("aoe", level).mob_hp
    single = pack * mob_hp / caster_rotation(class_name, stats, cls.spells, cls, ranks, Target(0, 0)).dps
    result = aoe_pull(class_name, stats, cls.spells, cls, ranks, pack, mob_hp,
                      assumptions=Assumptions.load().with_values(**assumed))
    return result, single


def test_warlocks_clear_packs_with_their_aoe():
    result, single = pull("warlock", "warlock-destruction-pve")
    assert result.spell in ("Rain of Fire", "Hellfire") and result.seconds < single


def test_without_an_aoe_spell_the_rotation_clears_the_pack():
    result, single = pull("priest", "priest-shadow")          # no Holy Nova talent
    assert (result.spell, result.seconds) == ("single target", pytest.approx(single))
    result, single = pull("druid", "druid-balance", level=30)  # Hurricane isn't learned yet
    assert (result.spell, result.seconds) == ("single target", pytest.approx(single))


def test_talented_holy_nova_and_hurricane_join_the_choice():
    result, single = pull("priest", "priest-holy")
    assert result.spell == "Holy Nova" and result.seconds < single
    result, single = pull("druid", "druid-balance")
    assert result.spell == "Hurricane" and result.seconds < single


def test_a_lone_mob_never_takes_longer_than_the_rotation():
    for class_name, build_id in (("warlock", "warlock-affliction"), ("shaman", "shaman-elemental")):
        result, single = pull(class_name, build_id, pack=1)
        assert result.seconds <= single + 1e-9


def test_chain_lightning_falloff_is_a_toggle():
    with_falloff, _ = pull("shaman", "shaman-elemental")
    without, _ = pull("shaman", "shaman-elemental", chain_jump_falloff_pct=0)
    assert without.seconds <= with_falloff.seconds
