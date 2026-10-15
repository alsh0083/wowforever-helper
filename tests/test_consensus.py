from pathlib import Path

from wowforever.classes.mage import LAYOUT
from wowforever.consensus import Consensus
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.normalize import normalize_class, read_tables
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
MAGE, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205"), LAYOUT,
                          parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                          wago_build="1.60.1.70205")
C = Consensus.load()
C_PATH = Path(__file__).resolve().parents[1] / "config" / "consensus.toml"

# Owner rules (#23): no gold/boost sellers; robots-disallowed sites excluded. Icy Veins allows
# robots but returns 403 to automated fetches, so it's excluded too.
BANNED = ("wowhead.com", "reddit.com", "overgear", "boostroom", "expcarry", "lfcarry", "mmojugg",
          "misti.services", "icy-veins.com")


def test_shipped_consensus_is_consistent_with_real_talents():
    assert C.problems(MAGE) == []


def test_covers_every_v0_and_v1_scenario():
    assert set(C.scenarios) == {"questing", "aoe", "dungeon", "raid", "wpvp_melee", "wpvp_caster",
                                "stealth_ambush", "battleground"}


def test_sources_respect_owner_rules():
    for key, src in C.sources.items():
        assert not any(b in src["url"] for b in BANNED), key
        assert src["era"] in ("forever", "classic", "tbc", "mixed")


def test_classic_only_evidence_on_a_changed_talent_is_low_confidence():
    # battleground tiers cite only Classic sources, and Forever changed Ice Barrier
    assert MAGE.talent_named("Ice Barrier").classic_status == "changed"
    assert C.tier_confidence("battleground", "Ice Barrier", MAGE) == "low"
    # wpvp_melee tiers include a Forever source, so the scenario's confidence applies
    assert C.tier_confidence("wpvp_melee", "Ice Barrier", MAGE) == "medium"


def test_tiers_are_per_class():
    # mage's tiers moved under [tiers.mage.*] unchanged (#321); other classes have none until #320
    assert C.tiers_for("mage")["wpvp_caster"]["core"] == ("Ice Barrier", "Ice Block", "Cold Snap")
    assert set(C.tiers_for("mage")) == {"wpvp_melee", "wpvp_caster", "stealth_ambush", "battleground", "questing"}
    assert C.tiers_for("no-such-class") == {}


def test_tier_names_are_checked_against_their_own_class(tmp_path):
    path = tmp_path / "consensus.toml"
    path.write_text(Path(C_PATH).read_text(encoding="utf-8")
                    + '\n[tiers.rogue.wpvp_melee]\ncore = ["Ice Block"]\nsources = []\n', encoding="utf-8")
    loaded = Consensus.load(path)
    assert loaded.problems(MAGE) == []                      # mage's tiers still check against mage
    assert loaded.tiers_for("rogue")["wpvp_melee"]["core"] == ("Ice Block",)
    rogue = Dataset.load(latest_dataset_path()).class_data("rogue")
    assert loaded.problems(rogue) == ["tiers.rogue.wpvp_melee: 'Ice Block' is not a talent"]


def test_researched_classes_have_pvp_tiers_that_name_their_own_talents():
    # #320 (docs/research/pvp-core-talents.md): only classes with Forever-era PvP evidence get tiers
    data = Dataset.load(latest_dataset_path())
    with_tiers = {"mage", "warlock", "warrior", "paladin", "rogue"}
    for name in ("mage", "rogue", "hunter", "warrior", "druid", "paladin", "priest", "shaman", "warlock"):
        assert C.problems(data.class_data(name)) == [], name
        has = all(C.tiers_for(name).get(s, {}).get("core") for s in ("wpvp_melee", "wpvp_caster", "stealth_ambush"))
        assert has == (name in with_tiers), name
    assert C.tiers_for("warrior")["wpvp_melee"]["core"] == ("Mortal Strike", "Improved Hamstring")
