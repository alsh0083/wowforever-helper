"""wowforevertalents.com talent pages as the rank-text source (#458)."""

from pathlib import Path

import pytest

from wowforever.sources.wowforevertalents import TalentPage, parse_talent, talent_slugs, talent_url

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
