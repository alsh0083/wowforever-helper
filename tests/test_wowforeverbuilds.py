"""wowforeverbuilds.com spec guides as a source of community standards (#460)."""

from pathlib import Path

import pytest

from wowforever.sources.wowforeverbuilds import (Calculator, GuideBuild, decode, guide_slugs, parse_calculator,
                                                 parse_guide)

FIX = Path(__file__).resolve().parent / "fixtures" / "wowforeverbuilds"


def page(name):
    return (FIX / f"{name}.html").read_text(encoding="utf-8")


def calc():
    return parse_calculator(page("talents-druid"))


def test_calculator_lists_each_tree_in_code_order():
    c = calc()
    assert (c.class_slug, c.build) == ("druid", "1.60.1.70532")
    assert [len(tree) for tree in c.trees] == [16, 20, 16]
    assert c.trees[1][:3] == (("Ferocity", 5), ("Heart of the Wild", 5), ("Feral Swiftness", 2))
    assert c.trees[1][-1] == ("Berserk", 1)


def test_decode_the_feral_guide_build():
    # one digit per talent in calculator order, trees split by "-", missing trailing digits are 0
    assert decode("-55200332120132012501-05503", calc()) == {
        "Ferocity": 5, "Heart of the Wild": 5, "Feral Swiftness": 2, "Thick Hide": 3, "Shredding Attacks": 3,
        "Savage Fury": 2, "Feral Charge": 1, "Sharpened Claws": 2, "Primal Bite": 1, "Predatory Strikes": 3,
        "Blood Frenzy": 2, "Leader of the Pack": 1, "Natural Instinct": 2, "Natural Reaction": 5, "Berserk": 1,
        "Furor": 5, "Naturalist": 5, "Natural Shapeshifter": 3,
    }


def test_decode_rejects_codes_that_dont_fit_the_calculator():
    with pytest.raises(ValueError, match="Feral Combat/Thick Hide: rank 4 of 3"):
        decode("-55200432120132012501", calc())
    with pytest.raises(ValueError, match="Balance: 17 digits for 16 talents"):
        decode("11111111111111111", calc())
    with pytest.raises(ValueError, match="4 trees"):
        decode("---", calc())
    with pytest.raises(ValueError, match="not a digit"):
        decode("5x", calc())


def test_guide_page_gives_the_build_link_and_date():
    guide = parse_guide(page("guide-feral-combat-druid-pve-guide"), "feral-combat-druid-pve-guide")
    assert guide == GuideBuild(
        slug="feral-combat-druid-pve-guide", class_slug="druid", code="-55200332120132012501-05503",
        modified="2026-10-24",
        title="Feral Druid tank guide: level 60 bear build with Primal Bite, Berserk and Natural Reaction",
    )
    assert guide.url == "https://wowforeverbuilds.com/guide/feral-combat-druid-pve-guide"


def test_class_listing_gives_the_spec_guides_once_each():
    assert guide_slugs(page("guides-druid")) == [
        "balance-druid-pve-guide", "balance-druid-pvp-guide", "feral-combat-druid-pve-guide",
        "feral-combat-druid-pvp-guide", "restoration-druid-pve-guide", "restoration-druid-pvp-guide",
    ]
