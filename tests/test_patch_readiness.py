"""Patch process (#366): a readiness report for a new build, the dataset pin can't lag silently, and the
update summary points to the next step."""

import re
from pathlib import Path

from wowforever.schema import DATASET_PIN, DATASETS_DIR, latest_dataset_path, newest_saved_dataset
from wowforever.toml_cache import load_toml

ROOT = Path(__file__).resolve().parents[1]


def _key(path):
    return tuple(int(p) for p in path.stem.split("."))


def test_newest_saved_dataset_ignores_the_pin(tmp_path):
    for build in ("1.60.1.70291", "1.60.1.70425"):
        (tmp_path / f"{build}.json").write_text("{}", encoding="utf-8")
    assert newest_saved_dataset(tmp_path).stem == "1.60.1.70425"
    assert newest_saved_dataset().parent == DATASETS_DIR
    assert _key(newest_saved_dataset()) >= _key(latest_dataset_path())


def test_a_lagging_pin_names_its_tracking_issue():
    # the model may read an older build than the newest saved one only while an issue tracks the move
    if _key(latest_dataset_path()) < _key(newest_saved_dataset()):
        assert re.search(r"#\d+", DATASET_PIN.read_text(encoding="utf-8")), "config/dataset.toml must name the issue"


def test_readiness_on_the_pinned_build_is_clean():
    from wowforever.readiness import readiness

    problems = readiness(latest_dataset_path(), tables_dir=ROOT / "no-such-folder")
    # without cached client tables the group-buff check is skipped and says so; nothing else is open
    assert problems == ["group buffs: client tables not cached at no-such-folder, not checked"]


def test_readiness_flags_what_an_older_build_breaks():
    from wowforever.readiness import readiness

    old = DATASETS_DIR / "1.60.1.70291.json"
    problems = readiness(old, tables_dir=ROOT / "no-such-folder")
    # today's builds put 5 points in Critical Mass, which had 3 ranks on 70291
    assert any(p.startswith("mage: build deep-fire: ") and "Critical Mass" in p for p in problems)
    # rules written for 70425 text don't all match 70291 (Grim Reach didn't exist)
    assert any(p.startswith("warlock: ") for p in problems)


def test_readiness_command_exits_non_zero_while_problems_are_open(capsys):
    from wowforever.__main__ import main

    code = main(["patch-readiness", "--dataset", str(DATASETS_DIR / "1.60.1.70291.json"),
                 "--tables", str(ROOT / "no-such-folder")])
    assert code == 1 and "mage: build deep-fire" in capsys.readouterr().out


def test_the_runbook_exists_and_names_the_steps():
    text = (ROOT / "docs" / "patch-update.md").read_text(encoding="utf-8")
    for step in ("update", "patch-readiness", "config/dataset.toml", "refresh_community_builds", "derive_leveling_builds",
                 "derive_opponent_kits", "validate-logs", "dashboard"):
        assert step in text, step
