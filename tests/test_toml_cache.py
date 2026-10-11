"""Config TOML is parsed once per process (#254): reports re-read config/*.toml ~218k times."""

import tomllib
from pathlib import Path
from types import SimpleNamespace

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
    """Count toml_cache's own parses (other modules' tomllib calls, e.g. at import, don't count)."""
    count: list[str] = []          # the text of every parse

    def counting(text):
        count.append(text)
        return tomllib.loads(text)

    monkeypatch.setattr(toml_cache, "tomllib", SimpleNamespace(loads=counting))
    toml_cache.clear()
    yield count
    toml_cache.clear()


def test_a_file_is_parsed_once(tmp_path, parses):
    path = tmp_path / "a.toml"
    path.write_text("x = 1\n[s]\ny = [1, 2]\n", encoding="utf-8")
    assert [load_toml(path) for _ in range(5)] == [{"x": 1, "s": {"y": [1, 2]}}] * 5
    assert len(parses) == 1


def test_clear_forgets_parsed_files(tmp_path, parses):
    path = tmp_path / "a.toml"
    path.write_text("x = 1\n", encoding="utf-8")
    assert load_toml(path) == {"x": 1}
    path.write_text("x = 22\n", encoding="utf-8")
    assert load_toml(path) == {"x": 1}          # no re-check within a run
    toml_cache.clear()
    assert load_toml(path) == {"x": 22}
    assert len(parses) == 2


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
    assert parses and len(parses) == len(set(parses))     # no file parsed twice (imports may parse others once)


@pytest.mark.parametrize("name", MIGRATED)
def test_config_reads_go_through_the_cache(name):
    assert "tomllib.loads(" not in (SRC / name).read_text(encoding="utf-8"), name


def test_a_section_is_a_copy_of_just_that_table(tmp_path, parses):
    from wowforever.toml_cache import load_section
    path = tmp_path / "a.toml"
    path.write_text("[mage]\nx = [1]\n[rogue]\nx = [2]\n", encoding="utf-8")
    section = load_section(path, "mage")
    assert section == {"x": [1]}
    section["x"].append(9)
    assert load_section(path, "mage") == {"x": [1]} and load_toml(path)["rogue"] == {"x": [2]}
    with pytest.raises(KeyError):
        load_section(path, "priest")
    assert len(parses) == 1


def test_assumptions_and_consensus_parse_once(parses):
    from wowforever.assumptions import Assumptions
    from wowforever.consensus import Consensus
    for _ in range(10):
        assert Assumptions.load()["sub20_spell_penalty"] in (True, False)
        Consensus.load()
    assert len(parses) == 2


@pytest.mark.parametrize("name", ["assumptions.py", "consensus.py"])
def test_loaders_read_through_the_cache(name):
    assert "tomllib.loads(" not in (SRC / name).read_text(encoding="utf-8"), name


def test_class_sections_read_only_their_section():
    for name in ("gear.py", "melee_stats.py"):
        text = (SRC / name).read_text(encoding="utf-8")
        assert "load_section(" in text and "load_toml(CASTERS)[" not in text and "load_toml(CONFIG)[class_name]" not in text, name
