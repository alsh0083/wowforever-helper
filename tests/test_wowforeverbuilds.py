"""wowforeverbuilds.com spec guides as a source of community standards (#460)."""

import dataclasses
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from wowforever.schema import ClassData, Prerequisite, Talent, Tree
from wowforever.sources.wowforeverbuilds import (Calculator, GuideBuild, Snapshot, calculator_errors, decode, fetch,
                                                 guide_slugs, load_history, load_snapshot, parse_calculator,
                                                 parse_guide, standard_build, title_misses)

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


def test_calculator_keeps_each_talents_prerequisite():
    feral = calc().trees[1]
    assert [(feral[i][0], feral[need[0]][0], need[1]) for i, need in enumerate(calc().requires[1]) if need] == [
        ("Shifting Power", "Shredding Attacks", 3), ("Primal Bite", "Savage Fury", 2),
        ("Blood Frenzy", "Sharpened Claws", 2), ("Improved Shifting Power", "Shifting Power", 1),
        ("Rend and Tear", "Predatory Strikes", 3), ("Berserk", "Leader of the Pack", 1)]
    assert [len(tree) for tree in calc().requires] == [16, 20, 16]


# ---- part 2: a guide's digits follow the calculator in place when its code was last changed (#460) ----
# Tree One goes from A(5) B(3) C(1) to A(5) D(5) C(1): B is replaced in the same slot, so an old code still decodes,
# to talents nobody picked. Tree Two never changes. Our trees are the new ones.

def mini_calc(build, middle):
    return Calculator("testclass", build, ("One", "Two"), (
        (("A", 5), middle, ("C", 1)), (("X", 5),),
    ), (((0, 0), (0, 1), (1, 0)), ((0, 0),)), ((None, None, (0, 5)), (None,)))     # C needs A at rank 5


OLD, NEW = mini_calc("1.60.1.100", ("B", 3)), mini_calc("1.60.1.200", ("D", 5))
OURS = ClassData(
    "testclass",
    (Tree(1, "One", (1, 2, 3)), Tree(2, "Two", (4,))),
    (Talent(1, "A", 1, 0, 0, 5, (), ()), Talent(2, "D", 1, 0, 1, 5, (), ()),
     Talent(3, "C", 1, 1, 0, 1, (), (), Prerequisite(1, 5)), Talent(4, "X", 2, 0, 0, 5, (), ())),
)


def snap(date, calculator, title="", **codes):
    return Snapshot(date, {"testclass": calculator},
                    {slug: GuideBuild(slug, "testclass", code, date, title or slug) for slug, code in codes.items()})


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
    assert why == ("g: the build and the calculator both changed between 2026-10-24 and 2026-11-05, "
                   "and the two calculators read it as two different plausible builds")
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
                         (((0, 1), (0, 0), (1, 0)), ((0, 0),)), ((None, None, (1, 5)), (None,)))
    history = [snap("2026-10-24", swapped, g="451"), snap("2026-11-05", NEW, g="451")]
    assert standard_build("g", history, OURS) == ({"D": 4, "A": 5, "C": 1}, "")   # read with `swapped`
    # code and calculator changed together: `swapped` reads 541 as D5 A4 C1, which breaks C's prerequisite (A at 5)
    history = history[:1] + [snap("2026-11-05", NEW, g="541")]
    assert standard_build("g", history, OURS) == ({"A": 5, "D": 4, "C": 1}, "")


def test_the_build_must_be_legal_on_our_trees():
    ranks, why = standard_build("g", [snap("2026-11-05", NEW, g="401")], OURS)
    assert ranks is None
    assert why.startswith("g: not legal: C requires")


def test_codes_the_calculator_cant_read_and_missing_guides():
    assert standard_build("g", [snap("2026-11-05", NEW, g="5555")], OURS) == (None, "g: One: 4 digits for 3 talents")
    assert standard_build("h", [snap("2026-11-05", NEW, g="5")], OURS) == (None, "h: not in the 2026-11-05 snapshot")


# ---- part 3: when code and calculator changed in the same gap, the evidence decides (#460) ----

def test_calculator_errors_are_point_gates_and_prerequisites():
    assert calculator_errors({"A": 5, "D": 4, "C": 1}, NEW) == []
    assert calculator_errors({"A": 4, "C": 1}, NEW) == ["One/C: needs 5 points in earlier rows, has 4",
                                                        "One/C: needs A at rank 5"]
    assert calculator_errors({"D": 2, "C": 1, "X": 5}, NEW) == ["One/C: needs 5 points in earlier rows, has 2",
                                                                "One/C: needs A at rank 5"]


def test_title_misses_names_the_build_skips_and_longer_names_win():
    names = ["Berserk", "Bite", "Primal Bite", "Furor"]
    assert title_misses({"Berserk": 1, "Primal Bite": 1}, "Bear build with Primal Bite and berserk", names) == []
    assert title_misses({"Berserk": 1}, "Bear build with Primal Bite and Berserk", names) == ["Primal Bite"]
    assert title_misses({}, "Feral guide: Bite, then Furorious", names) == ["Bite"]


def test_the_title_picks_the_reading():
    history = [snap("2026-10-24", OLD, g="521"), snap("2026-11-05", NEW, title="A build with D", g="531")]
    assert standard_build("g", history, OURS) == ({"A": 5, "D": 3, "C": 1}, "")
    history[1] = snap("2026-11-05", NEW, title="A build with B", g="531")
    assert standard_build("g", history, OURS) == (None, "g: One: the build was made on the 1.60.1.100 calculator "
                                                        "(2026-10-24), whose tree differs from ours")


def test_readings_that_break_their_own_trees_dont_count():
    history = [snap("2026-10-24", OLD, g="521"), snap("2026-11-05", NEW, g="021")]
    assert standard_build("g", history, OURS) == (None, "g: the build and the calculator both changed between "
                                                        "2026-10-24 and 2026-11-05, and the two calculators read it "
                                                        "as no plausible build")


def test_readings_that_agree_are_kept():
    history = [snap("2026-10-24", OLD, g="5"), snap("2026-11-05", NEW, g="501")]
    assert standard_build("g", history, OURS) == ({"A": 5, "C": 1}, "")


# ---- part 4: saved snapshots of the site are the history (#460) ----

DRUID_GUIDES = ["balance-druid-pve-guide", "balance-druid-pvp-guide", "feral-combat-druid-pve-guide",
                "feral-combat-druid-pvp-guide", "restoration-druid-pve-guide", "restoration-druid-pvp-guide"]


class FakeSite:
    """The druid calculator and listing; every guide URL serves the saved feral guide."""

    def __init__(self):
        self.asked = []

    def __call__(self, url):
        self.asked.append(url)
        if url == "https://wowforeverbuilds.com/talents/druid":
            return page("talents-druid")
        if url == "https://wowforeverbuilds.com/guides/druid":
            return page("guides-druid")
        assert url.startswith("https://wowforeverbuilds.com/guide/"), url
        return page("guide-feral-combat-druid-pve-guide")


def offline(url):
    raise AssertionError(f"fetched {url}")


def test_fetch_saves_the_calculator_listing_and_guides(tmp_path):
    site, naps = FakeSite(), []
    manifest_path = fetch(http_get=site, raw_dir=tmp_path / "20261031", classes=("druid",), sleep=naps.append)
    assert site.asked == ["https://wowforeverbuilds.com/talents/druid", "https://wowforeverbuilds.com/guides/druid",
                          *(f"https://wowforeverbuilds.com/guide/{slug}" for slug in DRUID_GUIDES)]
    assert naps == [1.5] * 7                                    # a pause before every page but the first
    assert manifest_path == tmp_path / "20261031" / "manifest.json"
    assert sorted(p.name for p in (tmp_path / "20261031").glob("*.html.gz")) == sorted(
        ["talents-druid.html.gz", "guides-druid.html.gz", *(f"guide-{slug}.html.gz" for slug in DRUID_GUIDES)])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert {k: manifest[k] for k in ("source", "url", "captured", "classes", "pages")} == {
        "source": "wowforeverbuilds.com", "url": "https://wowforeverbuilds.com", "captured": "2026-10-31",
        "classes": ["druid"], "pages": 8}
    assert len(manifest["sha256"]) == 64
    saved = (tmp_path / "20261031" / "talents-druid.html.gz").read_bytes()
    assert gzip.decompress(saved) == (FIX / "talents-druid.html").read_bytes()   # as fetched, byte for byte
    assert saved[4:8] == bytes(4)                                # no timestamp: the same page saves the same bytes
    pages = sorted((tmp_path / "20261031").glob("*.html.gz"))
    assert manifest["sha256"] == hashlib.sha256(b"".join(gzip.decompress(p.read_bytes()) for p in pages)).hexdigest()


def test_a_saved_snapshot_is_never_fetched_again(tmp_path):
    first = fetch(http_get=FakeSite(), raw_dir=tmp_path / "20261031", classes=("druid",), sleep=lambda s: None)
    assert fetch(http_get=offline, raw_dir=tmp_path / "20261031", classes=("druid",), sleep=lambda s: None) == first


def test_load_snapshot_reads_the_calculators_and_guides(tmp_path):
    fetch(http_get=FakeSite(), raw_dir=tmp_path / "20261031", classes=("druid",), sleep=lambda s: None)
    snapshot = load_snapshot(tmp_path / "20261031")
    assert snapshot.date == "2026-10-31"
    assert list(snapshot.calculators) == ["druid"] and snapshot.calculators["druid"] == calc()
    assert sorted(snapshot.guides) == DRUID_GUIDES
    assert snapshot.guides["balance-druid-pvp-guide"].code == "-55200332120132012501-05503"
    assert snapshot.guides["balance-druid-pvp-guide"].slug == "balance-druid-pvp-guide"


def test_load_snapshot_refuses_edited_pages(tmp_path):
    fetch(http_get=FakeSite(), raw_dir=tmp_path / "20261031", classes=("druid",), sleep=lambda s: None)
    path = tmp_path / "20261031" / "guide-balance-druid-pve-guide.html.gz"
    path.write_bytes(gzip.compress(gzip.decompress(path.read_bytes()).replace(b"55200332", b"55200333")))
    with pytest.raises(ValueError, match="pages changed since the snapshot was saved"):
        load_snapshot(tmp_path / "20261031")


def test_load_history_is_every_saved_snapshot_oldest_first(tmp_path):
    for name in ("20261107", "20261031"):
        fetch(http_get=FakeSite(), raw_dir=tmp_path / name, classes=("druid",), sleep=lambda s: None)
    (tmp_path / "20261114").mkdir()                             # no manifest: an interrupted fetch
    (tmp_path / "README.md").write_text("notes", encoding="utf-8")
    assert [s.date for s in load_history(tmp_path)] == ["2026-10-31", "2026-11-07"]


# ---- #463: a build picked for other numbers isn't a current standard ----
# The calculator carries each talent's rank text; every talent in a tree the build uses must read as ours does.

OUR_TEXT = {"A": tuple(f"A by {n}%." for n in range(1, 6)), "D": tuple(f"D by {n}%." for n in range(1, 6)),
            "C": ("C once.",), "X": tuple(f"X by {n}%." for n in range(1, 6))}
OURS_TEXT = dataclasses.replace(OURS, talents=tuple(dataclasses.replace(t, rank_text=OUR_TEXT[t.name])
                                                     for t in OURS.talents))


def site(**changed):
    text = OUR_TEXT | changed
    return dataclasses.replace(NEW, texts=((text["A"], text["D"], text["C"]), (text["X"],)))


def test_the_calculator_keeps_each_talents_rank_text():
    c = calc()
    assert len(c.texts) == len(c.trees) and all(len(t) == len(n) for t, n in zip(c.texts, c.trees))
    assert c.texts[0][0][1] == "Reduces the cast time of your Wrath spell by 0.2 sec and its Mana cost by 20%."
    assert [len(text) for text in c.texts[1][3]] and len(c.texts[1][3]) == 3        # Feral Instinct, 3 ranks


def test_the_same_rank_text_keeps_the_build():
    spaced = tuple(f"A  by {n}%" for n in range(1, 6))         # spacing and a final full stop don't count
    for c in (site(), site(A=spaced)):
        assert standard_build("g", [snap("2026-11-05", c, g="541")], OURS_TEXT) == ({"A": 5, "D": 4, "C": 1}, "")


def test_changed_rank_text_in_a_used_tree_drops_the_build():
    c = site(D=tuple(f"D by {2 * n}%." for n in range(1, 6)), C=("C twice.",))
    assert standard_build("g", [snap("2026-11-05", c, g="541")], OURS_TEXT) == (
        None, "g: One: the build was made on the 1.60.1.200 calculator (2026-11-05), whose rank text differs "
              "from ours for D, C")


def test_changed_rank_text_in_a_tree_the_build_leaves_empty_does_not_matter():
    c = site(X=tuple(f"X by {9 * n}%." for n in range(1, 6)))
    assert standard_build("g", [snap("2026-11-05", c, g="541-0")], OURS_TEXT)[0] == {"A": 5, "D": 4, "C": 1}


def test_numbers_may_differ_by_rounding_and_how_they_are_written():
    ours = dataclasses.replace(OURS_TEXT, talents=tuple(
        dataclasses.replace(t, rank_text=("Deals 147 damage over 3 sec.",)) if t.name == "C" else t
        for t in OURS_TEXT.talents))
    for text, kept in (("Deals 146 damage over 3.0 sec.", True), ("Deals 160 damage over 3 sec.", False),
                       ("Deals 147 damage over 3 seconds.", False)):
        ranks, _ = standard_build("g", [snap("2026-11-05", site(C=(text,)), g="541")], ours)
        assert (ranks is not None) == kept, text
