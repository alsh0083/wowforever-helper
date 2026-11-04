"""Community standards from current sources (#460): one build per slot, wowforeverbuilds.com's guide first, then
talentsforever.com's top builds, each taken as published or dropped. Fixtures: talentsforever.com's rogue builds
page and export of 4 Nov 2026 (CC BY 4.0), read on the saved 70755 dataset."""

import json
from pathlib import Path

from wowforever.schema import DATASETS_DIR, Dataset
from wowforever.sourced import Candidate, Sourced, on_our_trees, pick
from wowforever.sources.talentsforever import popular_builds

FIX = Path(__file__).resolve().parent / "fixtures" / "talentsforever"
ROGUE = Dataset.load(DATASETS_DIR / "1.60.1.70755.json").class_data("rogue")
ROWS = popular_builds((FIX / "rogue-builds-20261104.html").read_text(encoding="utf-8"),
                      json.loads((FIX / "rogue-export-20261104.json").read_text(encoding="utf-8")))
TOP = [Candidate(None, r["final"], "talentsforever.com", f"https://talentsforever.com/rogue/60/{r['code']}", r["name"],
                 f"top build #{r['rank']}, saved {r['saved_total']}") for r in ROWS]
ARCH = {"deep": 31, "hybrid": 15, "recognized": ("Assassination/Subtlety",)}


def test_a_complete_top_build_reads_on_our_trees():
    ids, why = on_our_trees(ROWS[0]["final"], ROGUE)          # Combat Rogue 15/36/0
    assert why == "" and sum(ids.values()) == 51
    assert ids[ROGUE.talent_named("Coup de Grace").talent_id] == ROWS[0]["final"]["Coup de Grace"]


def test_builds_are_dropped_not_adjusted():
    full = dict(ROWS[0]["final"])
    assert on_our_trees(full | {"Murder": 2}, ROGUE) == (None, "Murder: not a talent on our trees")
    assert on_our_trees(full | {"Lethality": 5}, ROGUE) == (None, "Lethality: rank 5 is over its cap 2")
    assert on_our_trees(ROWS[2]["final"], ROGUE) == (None, "spends 45 of 51 points")   # Assassination 32/11/2
    reach = full | {"Malice": full["Malice"] - 1, "Premeditation": 1}       # Subtlety row 3 with no Subtlety points
    ids, why = on_our_trees(reach, ROGUE)
    assert ids is None and why.startswith("not legal: ")


def test_one_build_per_slot_guides_first_then_the_top_builds_in_order():
    guide = Candidate("PvE", ROWS[1]["final"], "wowforeverbuilds.com", "https://wowforeverbuilds.com/guide/combat",
                      "Combat Rogue PvE guide", "spec guide")
    chosen, skipped = pick(ROGUE, [guide], TOP, **ARCH)
    assert [(s.archetype, s.focus, s.title) for s in chosen] == [
        ("deep Combat", "PvE", "Combat Rogue PvE guide"),
        ("deep Assassination", "PvE", "Assassination Rogue 35/11/5"),
        ("deep Subtlety", "PvE", "Subtlety Rogue 12/8/31"),
    ]
    assert skipped == [
        "Combat Rogue 15/36/0: deep Combat PvE already has Combat Rogue PvE guide",
        "Combat Rogue 16/35/0: deep Combat PvE already has Combat Rogue PvE guide",
        "Assassination Rogue 32/11/2: spends 45 of 51 points",
    ]
    assert chosen[1] == Sourced("deep Assassination", "PvE", ROWS[3]["final"], "talentsforever.com", TOP[3].url,
                                "Assassination Rogue 35/11/5", "top build #4, saved 43")


def test_a_pvp_guide_takes_the_pvp_slot_and_top_builds_only_fill_pve():
    guide = Candidate("PvP", ROWS[0]["final"], "wowforeverbuilds.com", "https://wowforeverbuilds.com/guide/c-pvp",
                      "Combat Rogue PvP guide", "spec guide")
    chosen, _ = pick(ROGUE, [guide], TOP, **ARCH)
    assert {(s.archetype, s.focus) for s in chosen} == {
        ("deep Combat", "PvP"), ("deep Combat", "PvE"), ("deep Assassination", "PvE"), ("deep Subtlety", "PvE")}


def test_build_toml_labels_the_source_and_loads_as_a_community_build(tmp_path):
    import tomllib

    from wowforever.builds import load_builds
    from wowforever.sourced import build_toml

    s = Sourced("deep Assassination", "PvE", ROWS[3]["final"], "talentsforever.com", TOP[3].url,
                "Assassination Rogue 35/11/5", "top build #4, saved 43")
    build_id, text = build_toml("rogue", s, "2026-11-04")
    assert build_id == "rogue-assassination"
    assert text.startswith("# Community standard (#460) from talentsforever.com, saved 2026-11-04: top build #4, "
                           "saved 43. Data (c) Talents Forever, https://talentsforever.com, CC BY 4.0.\n")
    raw = tomllib.loads(text)
    assert (raw["id"], raw["pair"], raw["variant"], raw["origin"], raw["sources"]) == (
        "rogue-assassination", "rogue-assassination", "PvE", "community", ["talentsforever_top"])
    assert raw["final"] == ROWS[3]["final"]
    (tmp_path / f"{build_id}.toml").write_text(text, encoding="utf-8")
    [build] = load_builds(tmp_path)
    assert sum(build.final_ids(ROGUE).values()) == 51

    pvp = build_toml("rogue", Sourced("deep Combat", "PvP", ROWS[0]["final"], "wowforeverbuilds.com",
                                      "https://wowforeverbuilds.com/guide/c", "Combat PvP guide", "spec guide"), "2026-11-04")
    assert pvp[0] == "rogue-combat-pvp" and 'sources = ["wowforeverbuilds_guides"]' in pvp[1] and "CC BY" not in pvp[1]
