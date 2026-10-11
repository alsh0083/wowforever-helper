"""Indexed talent lookups and memoized spell scaling (#254 step 2): same answers as the linear scans."""

import pytest

from wowforever import schema
from wowforever.scenarios import scaled
from wowforever.schema import Dataset, latest_dataset_path, talent_aliases

CLASSES = Dataset.load(latest_dataset_path()).classes


def test_talent_lookups_match_a_linear_scan():
    for cls in CLASSES:
        for t in cls.talents:
            assert cls.talent(t.talent_id) is t
            matches = [u for u in cls.talents if u.name.lower() in talent_aliases(t.name)]
            if len(matches) == 1:
                assert cls.talent_named(t.name) is t
                assert cls.talent_named(t.name.upper()) is t
            else:
                with pytest.raises(KeyError):
                    cls.talent_named(t.name)
        with pytest.raises(KeyError):
            cls.talent(-1)
        with pytest.raises(KeyError):
            cls.talent_named("No Such Talent")


def test_renamed_talents_are_found_by_either_name():
    druid = next(c for c in CLASSES if c.class_name == "druid")
    assert druid.talent_named("Natural Instinct") is druid.talent_named("Predatory Instincts")


def test_talent_lookups_are_indexed():
    cls = CLASSES[0]
    cls.talent(cls.talents[0].talent_id)
    cls.talent_named(cls.talents[0].name)
    assert "_talents_by_id" in vars(cls) and "_talents_by_name" in vars(cls)


def test_talent_aliases_are_memoized_and_callers_get_their_own_set():
    first = talent_aliases("Frostbite")
    first.add("changed")
    before = schema._aliases.cache_info().hits
    assert talent_aliases("Frostbite") == {"frostbite"}
    assert talent_aliases("FROSTBITE") == {"frostbite"}
    assert schema._aliases.cache_info().hits >= before + 2


def test_scaled_is_memoized_and_unchanged():
    spells = [s for cls in CLASSES for s in cls.spells]
    for spell in spells:
        for level in (1, 10, 20, 30, 40, 50, 60):
            assert scaled(spell, level) == scaled.__wrapped__(spell, level)
    before = scaled.cache_info().hits
    assert scaled(spells[0], 60) == scaled.__wrapped__(spells[0], 60)
    assert scaled.cache_info().hits == before + 1
