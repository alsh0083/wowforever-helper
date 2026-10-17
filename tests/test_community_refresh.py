"""Refreshing hand-adjusted community builds from post-patch player data (#369)."""

import json
import tomllib
from pathlib import Path

from wowforever.builds import load_builds
from wowforever.schema import Dataset, latest_dataset_path

ROOT = Path(__file__).resolve().parents[1]
DS = Dataset.load(latest_dataset_path())


def build(class_name, build_id):
    return {b.id: b for b in load_builds(class_name=class_name)}[build_id]


def top(class_name):
    return json.loads((ROOT / "data" / "popularity" / f"{class_name}.json").read_text(encoding="utf-8"))["top"]


def test_adjusted_builds_say_what_moved():
    assert build("mage", "deep-fire").adjusted.startswith("1.60.1.70425: Fire Power")
    assert build("mage", "deep-frost").adjusted == ""


def test_closest_popular_build_shares_the_main_tree_and_most_points():
    from wowforever.community import closest_popular

    # Elemental is the post-patch #5 build (37/13/0) since the refresh: all 50 of the players' points (the 51st is
    # model-filled, tools/fill_open_points.py)
    match = closest_popular(build("shaman", "shaman-elemental"), DS.class_data("shaman"), top("shaman"))
    assert match["rank"] == 5 and match["overlap"] == 50
    # Deep Fire stays adjusted: its closest post-patch build (#4, 4 saves) shares only 36 points
    match = closest_popular(build("mage", "deep-fire"), DS.class_data("mage"), top("mage"))
    assert match["rank"] == 4 and match["overlap"] == 36
    assert closest_popular(build("priest", "priest-shadow"), DS.class_data("priest"), []) is None


def test_ties_go_to_the_most_saved():
    from wowforever.community import closest_popular

    b = build("shaman", "shaman-elemental")
    entry = next(t for t in top("shaman") if t["rank"] == 5)
    twins = [dict(entry, rank="a", saved=3), dict(entry, rank="b", saved=40)]
    assert closest_popular(b, DS.class_data("shaman"), twins)["rank"] == "b"


def test_refreshed_toml_takes_the_players_points_and_drops_the_mark():
    from wowforever.community import closest_popular, refreshed_toml

    b = build("shaman", "shaman-elemental")
    path = ROOT / "config" / "builds" / "shaman-elemental.toml"
    match = closest_popular(b, DS.class_data("shaman"), top("shaman"))
    text = refreshed_toml(path.read_text(encoding="utf-8"), match, window="since the Oct 15 patch (build 70425)")
    raw = tomllib.loads(text)
    assert raw["final"] == {k: v for k, v in match["final"].items() if v > 0}
    assert "adjusted" not in raw and raw["id"] == "shaman-elemental" and raw["origin"] == "community"
    assert "rank 5" in text and "since the Oct 15 patch (build 70425)" in text and "#369" in text


def test_dashboard_caption_names_an_adjusted_community_build():
    from wowforever.dashboard import standard_caption

    assert standard_caption({"origin": "community"}) == "Community standard"
    assert standard_caption({"origin": "community", "adjusted": "1.60.1.70425: x"}) == \
        "Community standard, points adjusted for 1.60.1.70425"
    assert standard_caption({"origin": "model"}) == "Model build, no community plan yet"
    assert standard_caption({"origin": "hand"}) == "Custom build, no community plan yet"
