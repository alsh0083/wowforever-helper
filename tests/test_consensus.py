from pathlib import Path

from wowforever.classes.mage import LAYOUT
from wowforever.consensus import Consensus
from wowforever.normalize import normalize_class, read_tables
from wowforever.sources.wowforevertalent import parse_page

FIX = Path(__file__).parent / "fixtures"
MAGE, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205"), LAYOUT,
                          parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                          wago_build="1.60.1.70205")
C = Consensus.load()

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
