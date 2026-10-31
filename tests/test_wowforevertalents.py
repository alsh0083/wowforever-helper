"""wowforevertalents.com talent pages as the rank-text source (#458)."""

from pathlib import Path

import pytest

from wowforever.sources.wowforevertalents import (TalentPage, as_page, class_trees, parse_talent, talent_slugs,
                                                  talent_url)

FIX = Path(__file__).resolve().parent / "fixtures" / "wowforevertalents"
HOTFIX_SOURCES = ("Forever client build 1.60.1.70707",
                  "the WoW: Forever client's hotfix cache, 30 October 2026 (DBCache.bin, build 70707)")


def page(name):
    return (FIX / f"{name}.html").read_text(encoding="utf-8")


def test_genesis_has_every_rank_in_order():
    genesis = parse_talent(page("druid-talents-genesis"))
    assert genesis == TalentPage(
        name="Genesis", class_name="Druid", tree="Balance", max_rank=5,
        ranks=tuple(f"Increases the periodic damage and healing done by your spells and abilities by {n}%."
                    for n in (2, 4, 6, 8, 10)),
        sources=HOTFIX_SOURCES,
    )


def test_a_hotfix_talent_with_one_rank():
    lacerate = parse_talent(page("druid-talents-lacerate"))
    assert (lacerate.name, lacerate.tree, lacerate.max_rank) == ("Lacerate", "Feral Combat", 1)
    assert lacerate.ranks == (
        "Lacerates the enemy target, making them bleed for 20 damage over 15 sec plus 10% weapon damage per "
        "existing application of Lacerate on the target. Causes a high amount of threat. This effect stacks up "
        "to 5 times on the same target.",)


def test_html_entities_and_multi_word_names():
    champion = parse_talent(page("paladin-talents-champion-of-the-light"))
    assert (champion.name, champion.class_name, champion.tree, champion.max_rank) == \
        ("Champion of the Light", "Paladin", "Retribution", 5)
    assert champion.ranks[4] == ("Increases your spell damage by up to 60% of your Intellect, and reduces the "
                                 "cast time of your Hammer of Wrath by 1 sec.")


def test_classic_wording_is_not_a_rank():
    incineration = parse_talent(page("mage-talents-incineration"))
    assert incineration.max_rank == 5 and len(incineration.ranks) == 5
    assert incineration.ranks[0].endswith("Fire Blast, Ice Lance, Arcane Blast, and Scorch spells by 2%.")


def test_rank_count_must_match_the_stated_ranks():
    broken = page("druid-talents-genesis").replace("5 ranks", "4 ranks", 1)
    with pytest.raises(ValueError, match="Genesis: 5 rank texts for 4 ranks"):
        parse_talent(broken)


def test_class_page_lists_each_talent_once_in_page_order():
    slugs = talent_slugs(page("druid"), "druid")
    assert len(slugs) == 52 and len(set(slugs)) == 52
    assert slugs[:4] == ["genesis", "nature-s-majesty", "nature-s-splendor", "eclipse"]
    assert slugs[-2:] == ["nature-s-swiftness", "improved-regrowth"]
    assert "lacerate" in slugs and "berserk" not in slugs
    assert talent_slugs(page("druid"), "mage") == []


def test_talent_url():
    assert talent_url("druid", "lacerate") == "https://wowforevertalents.com/druid/talents/lacerate/"


# ---- part 2: the class page's grid as the calculator page normalize reads (#458) ----

def node(trees, name):
    return next((tree["name"], t) for tree in trees for t in tree["talents"] if t["name"] == name)


def test_class_trees_reads_the_grid():
    trees = class_trees(page("druid"))
    assert [t["name"] for t in trees] == ["Balance", "Feral Combat", "Restoration"]
    assert sum(len(t["talents"]) for t in trees) == 52
    assert node(trees, "Improved Wrath") == ("Balance", {
        "name": "Improved Wrath", "row": 1, "col": 2, "maxRank": 5, "icon": "spell_nature_abolishmagic",
        "classic": {"status": "changed"}})
    assert node(trees, "Genesis")[1]["classic"] == {"status": "new"}
    assert node(trees, "Lacerate") == ("Feral Combat", {
        "name": "Lacerate", "row": 4, "col": 2, "maxRank": 1, "icon": "ability_druid_lacerate",
        "classic": {"status": "new"}})
    assert node(trees, "Bloom")[1]["row"] == 3 and node(trees, "Bloom")[1]["col"] == 4


def test_unflagged_talents_are_the_same_as_classic_and_tree_names_follow_our_layouts():
    trees = class_trees(page("priest"))
    assert [t["name"] for t in trees] == ["Discipline", "Holy", "Shadow"]       # the site says "Shadow Magic"
    statuses = {t["classic"]["status"] for tree in trees for t in tree["talents"]}
    assert statuses == {"same", "changed", "new"}


def fake(name, max_rank, tree="Balance"):
    return TalentPage(name, "Druid", tree, max_rank, tuple(f"{name} rank {r}" for r in range(1, max_rank + 1)), ())


def talents_for(trees):
    return {t["name"]: fake(t["name"], t["maxRank"], tree["name"]) for tree in trees for t in tree["talents"]}


def test_as_page_puts_each_rank_text_on_its_node():
    trees = class_trees(page("druid"))
    talents = talents_for(trees) | {"Genesis": parse_talent(page("druid-talents-genesis"))}
    result = as_page("druid", page("druid"), talents, game_build="1.60.1.70707", data_version="20261031")
    assert (result.class_id, result.game_build, result.page_data_version, result.popular) == \
        ("druid", "1.60.1.70707", "wowforevertalents-20261031", None)
    _, genesis = node(result.trees, "Genesis")
    assert genesis["ranks"][0] == {"rank": 1, "text": "Increases the periodic damage and healing done by your "
                                                      "spells and abilities by 2%."}
    assert [r["rank"] for r in genesis["ranks"]] == [1, 2, 3, 4, 5]
    assert node(result.trees, "Lacerate")[1]["ranks"] == [{"rank": 1, "text": "Lacerate rank 1"}]


def test_as_page_needs_every_talent_page_with_the_same_rank_count():
    trees = class_trees(page("druid"))
    talents = talents_for(trees)
    del talents["Bloom"]
    with pytest.raises(ValueError, match="no talent page for Bloom"):
        as_page("druid", page("druid"), talents, game_build="1.60.1.70707", data_version="20261031")
    talents = talents_for(trees) | {"Genesis": fake("Genesis", 3)}
    with pytest.raises(ValueError, match="Genesis: the grid has 5 ranks, its page 3"):
        as_page("druid", page("druid"), talents, game_build="1.60.1.70707", data_version="20261031")
