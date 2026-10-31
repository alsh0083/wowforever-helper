"""wowforeverbuilds.com spec guides as a source of community standards (#460)."""

from pathlib import Path

import pytest

from wowforever.schema import ClassData, Prerequisite, Talent, Tree
from wowforever.sources.wowforeverbuilds import (Calculator, GuideBuild, Snapshot, decode, guide_slugs,
                                                 parse_calculator, parse_guide, standard_build)

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


def test_calculator_keeps_each_talents_position():
    c = calc()
    assert c.positions[1][:3] == ((0, 1), (0, 2), (1, 0))
    assert c.positions[1][-1] == (6, 1)
    assert [len(tree) for tree in c.positions] == [16, 20, 16]


# ---- part 2: a guide's digits follow the calculator in place when its code was last changed (#460) ----
# Tree One goes from A(5) B(3) C(1) to A(5) D(5) C(1): B is replaced in the same slot, so an old code still decodes,
# to talents nobody picked. Tree Two never changes. Our trees are the new ones.

def mini_calc(build, middle):
    return Calculator("testclass", build, ("One", "Two"), (
        (("A", 5), middle, ("C", 1)), (("X", 5),),
    ), (((0, 0), (0, 1), (1, 0)), ((0, 0),)))


OLD, NEW = mini_calc("1.60.1.100", ("B", 3)), mini_calc("1.60.1.200", ("D", 5))
OURS = ClassData(
    "testclass",
    (Tree(1, "One", (1, 2, 3)), Tree(2, "Two", (4,))),
    (Talent(1, "A", 1, 0, 0, 5, (), ()), Talent(2, "D", 1, 0, 1, 5, (), ()),
     Talent(3, "C", 1, 1, 0, 1, (), (), Prerequisite(1, 5)), Talent(4, "X", 2, 0, 0, 5, (), ())),
)


def snap(date, calculator, **codes):
    return Snapshot(date, {"testclass": calculator},
                    {slug: GuideBuild(slug, "testclass", code, date, slug) for slug, code in codes.items()})


def test_the_danger_an_old_code_reads_as_legal_new_talents():
    assert decode("521", NEW) == {"A": 5, "D": 2, "C": 1}


def test_first_snapshot_is_read_with_its_own_calculator():
    assert standard_build("g", [snap("2026-11-05", NEW, g="541")], OURS) == ({"A": 5, "D": 4, "C": 1}, "")


def test_a_code_that_outlived_a_calculator_change_is_read_with_the_old_one():
    ranks, why = standard_build("g", [snap("2026-10-24", OLD, g="521"), snap("2026-11-05", NEW, g="521")], OURS)
    assert ranks is None
    assert why == ("g: One: the build was made on the 1.60.1.100 calculator (2026-10-24), "
                   "whose tree differs from ours")


def test_a_code_changed_after_the_calculator_is_read_with_the_new_one():
    history = [snap("2026-10-24", OLD, g="521"), snap("2026-11-05", NEW, g="521"), snap("2026-11-12", NEW, g="541")]
    assert standard_build("g", history, OURS) == ({"A": 5, "D": 4, "C": 1}, "")


def test_code_and_calculator_changed_in_the_same_gap():
    ranks, why = standard_build("g", [snap("2026-10-24", OLD, g="521"), snap("2026-11-05", NEW, g="531")], OURS)
    assert ranks is None
    assert why == ("g: the build and the calculator both changed between 2026-10-24 and 2026-11-05; "
                   "can't tell which trees it was made on")
    # unless the old calculator can't read the new code (B has 3 ranks)
    history = [snap("2026-10-24", OLD, g="521"), snap("2026-11-05", NEW, g="541")]
    assert standard_build("g", history, OURS) == ({"A": 5, "D": 4, "C": 1}, "")


def test_a_change_in_a_tree_the_build_leaves_empty_does_not_matter():
    history = [snap("2026-10-24", OLD, g="-5"), snap("2026-11-05", NEW, g="-5")]
    assert standard_build("g", history, OURS) == ({"X": 5}, "")
    history = [snap("2026-10-24", OLD, g="-4"), snap("2026-11-05", NEW, g="-5")]
    assert standard_build("g", history, OURS) == ({"X": 5}, "")


def test_a_reordered_calculator_is_a_change():
    swapped = Calculator("testclass", "1.60.1.200", ("One", "Two"), ((("D", 5), ("A", 5), ("C", 1)), (("X", 5),)),
                         (((0, 1), (0, 0), (1, 0)), ((0, 0),)))
    history = [snap("2026-10-24", swapped, g="451"), snap("2026-11-05", NEW, g="451")]
    assert standard_build("g", history, OURS) == ({"D": 4, "A": 5, "C": 1}, "")   # read with `swapped`
    ranks, why = standard_build("g", history[:1] + [snap("2026-11-05", NEW, g="541")], OURS)
    assert why.startswith("g: the build and the calculator both changed")


def test_the_build_must_be_legal_on_our_trees():
    ranks, why = standard_build("g", [snap("2026-11-05", NEW, g="401")], OURS)
    assert ranks is None
    assert why.startswith("g: not legal: C requires")


def test_codes_the_calculator_cant_read_and_missing_guides():
    assert standard_build("g", [snap("2026-11-05", NEW, g="5555")], OURS) == (None, "g: One: 4 digits for 3 talents")
    assert standard_build("h", [snap("2026-11-05", NEW, g="5")], OURS) == (None, "h: not in the 2026-11-05 snapshot")
