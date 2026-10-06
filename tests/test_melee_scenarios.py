

def test_dungeon_armor_scales_with_level():
    # #172: a flat level-60 armor understated low-level melee against Forever Logs
    import pytest

    from wowforever.melee_scenarios import _anchor_at, _config

    cfg = _config()
    at = lambda level: _anchor_at(cfg["questing"]["anchors"], level)[0] * cfg["dungeon"]["armor_share_of_questing"]
    assert at(60) == pytest.approx(cfg["dungeon"]["armor"], rel=0.01)
    assert at(20) < at(40) < at(60)
