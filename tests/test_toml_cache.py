"""Config TOML is parsed once per file version (#254): reports re-read config/*.toml ~218k times."""

import os
from pathlib import Path

import pytest

from wowforever import toml_cache
from wowforever.toml_cache import load_toml

SRC = Path(__file__).resolve().parent.parent / "src" / "wowforever"
MIGRATED = ["melee_stats.py", "melee_scenarios.py", "scenarios.py", "group.py", "gear.py",
            "classes/druid_rotation.py", "classes/hunter_rotation.py", "classes/paladin_rotation.py",
            "classes/rogue_rotation.py", "classes/shaman_rotation.py", "classes/warrior_rotation.py",
            "pvp/class_pvp.py", "pvp/kit_stats.py"]


@pytest.fixture
def parses(monkeypatch):
    """Count real parses: wrap the tomllib.loads that toml_cache calls."""
    count = [0]
    real = toml_cache.tomllib.loads

    def counting(text):
        count[0] += 1
        return real(text)

    monkeypatch.setattr(toml_cache.tomllib, "loads", counting)
    toml_cache.clear()
    yield count
    toml_cache.clear()


def test_a_file_is_parsed_once(tmp_path, parses):
    path = tmp_path / "a.toml"
    path.write_text("x = 1\n[s]\ny = [1, 2]\n", encoding="utf-8")
    assert [load_toml(path) for _ in range(5)] == [{"x": 1, "s": {"y": [1, 2]}}] * 5
    assert parses[0] == 1


def test_a_changed_file_is_parsed_again(tmp_path, parses):
    path = tmp_path / "a.toml"
    path.write_text("x = 1\n", encoding="utf-8")
    assert load_toml(path) == {"x": 1}
    path.write_text("x = 22\n", encoding="utf-8")
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    assert load_toml(path) == {"x": 22}
    assert parses[0] == 2


def test_callers_get_their_own_copy(tmp_path, parses):
    path = tmp_path / "a.toml"
    path.write_text("[s]\ny = [1, 2]\n", encoding="utf-8")
    first = load_toml(path)
    first["s"]["y"].append(3)
    first["z"] = 0
    assert load_toml(path) == {"s": {"y": [1, 2]}}


def test_hot_loaders_parse_each_file_once(parses):
    from wowforever import melee_scenarios, melee_stats, scenarios
    for _ in range(20):
        melee_stats.class_config("rogue")
        melee_scenarios._config()
        scenarios.default_params("questing", 20)
    assert parses[0] == 3


@pytest.mark.parametrize("name", MIGRATED)
def test_config_reads_go_through_the_cache(name):
    assert "tomllib.loads(" not in (SRC / name).read_text(encoding="utf-8"), name
