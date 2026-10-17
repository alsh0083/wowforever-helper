"""DoT mana efficiency (#390): a caster's Output carries the rotation with each DoT or cooldown dropped, and
the dungeon and raid scores take whichever variant scores best on the mana budget."""

from types import SimpleNamespace

import pytest

from wowforever.builds import load_builds
from wowforever.caster import caster_rotation
from wowforever.classes import class_module
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import Output, dungeon, raid_dps, stat_table
from wowforever.physical import Target
from wowforever.schema import Dataset, latest_dataset_path

P = class_module("priest")
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("priest"), P.TALENT_EFFECTS, P.UNMODELED)
BUILDS = {b.id: b.final_ids(CLS) for b in load_builds(class_name="priest")}
STATS = stat_table("priest").at(60)
ONE_MINUTE = SimpleNamespace(mana_per_second=0.0, fight_lengths=None, fight_seconds=60, extra_mana=0.0,
                             consumables=())


def test_raid_dps_takes_the_best_alternative():
    # A: 600 mana at 20/s lasts 30 s: (100 x 30 + 10 x 30) / 60 = 55. B: 10/s lasts the minute: 80.
    a = Output(100.0, 20.0, 10.0)
    assert raid_dps(a, 600.0, ONE_MINUTE) == pytest.approx(55)
    with_b = Output(100.0, 20.0, 10.0, alternatives=(Output(80.0, 10.0, 10.0),))
    assert raid_dps(with_b, 600.0, ONE_MINUTE) == pytest.approx(80)
    # a worse alternative never lowers the score
    with_c = Output(100.0, 20.0, 10.0, alternatives=(Output(50.0, 5.0, 10.0),))
    assert raid_dps(with_c, 600.0, ONE_MINUTE) == pytest.approx(55)


def test_caster_rotation_skips_named_spells():
    r = caster_rotation("priest", STATS, CLS.spells, CLS, BUILDS["priest-shadow"], Target(3, 0),
                        skip=("Devouring Plague",))
    assert "Devouring Plague" not in r.spells and "Shadow Word: Pain" in r.spells


def test_caster_output_offers_each_dot_dropped():
    from wowforever.classes.engines import caster_output

    out = caster_output("priest", STATS, CLS.spells, CLS, BUILDS["priest-shadow"], Target(3, 0))
    full = caster_rotation("priest", STATS, CLS.spells, CLS, BUILDS["priest-shadow"], Target(3, 0))
    assert len(out.alternatives) == len(full.spells) - 1          # every DoT and cooldown, not the filler
    dropped = caster_rotation("priest", STATS, CLS.spells, CLS, BUILDS["priest-shadow"], Target(3, 0),
                              skip=("Devouring Plague",))
    assert any(a.dps == pytest.approx(dropped.dps) for a in out.alternatives)
    assert all(a.alternatives == () for a in out.alternatives)


def test_smite_drops_devouring_plague_in_the_dungeon_shadow_keeps_it():
    # from the probe in #390, re-run with Twin Disciplines and Improved Shadow Word: Pain (#384): Smite drops
    # Devouring Plague, Shadow keeps it
    assert dungeon("priest", STATS, CLS.spells, CLS, BUILDS["priest-discipline-smite"]) == pytest.approx(187.16, abs=0.01)
    assert dungeon("priest", STATS, CLS.spells, CLS, BUILDS["priest-shadow"]) == pytest.approx(492.06, abs=0.01)
