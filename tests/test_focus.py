"""Focus scores (#28) on the real fixtures: direction checks, not golden values."""

from pathlib import Path

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.classes.mage import LAYOUT, SKILL_LINES, TALENT_EFFECTS, UNMODELED
from wowforever.consensus import Consensus
from wowforever.effects import attach_effects
from wowforever import melee_scenarios as ms
from wowforever.focus import class_pvp_score, pvp_core_talents
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells
from wowforever.pvp.duel import load_kits
from wowforever.sources.wowforevertalent import parse_page
from wowforever.stats import StatTable
from dataclasses import replace

FIX = Path(__file__).parent / "fixtures"
# the real builds on the dataset the model reads (config/dataset.toml)
from wowforever.schema import Dataset, latest_dataset_path  # noqa: E402
CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("mage"), TALENT_EFFECTS, UNMODELED)
# the owner's former hand-made Elementalist builds stay as fixtures (tests/fixtures/builds/)
# fixture builds naming talents a patch removed are left out
B = {b.id: b.final_ids(CLS) for b in [*load_builds(class_name="mage"), *load_builds(Path(__file__).parent / "fixtures" / "builds", class_name="mage")]
     if not b.unknown_talents(CLS)}
STATS, A = StatTable.load("mage").at(60), Assumptions.load()


def test_archetype_config():
    arch = Consensus.load().archetypes
    assert (arch["deep"], arch["hybrid"]) == (31, 15) and "Fire/Frost" in arch["recognized"]


def test_pvp_core_talents_come_from_consensus_tiers():
    assert {"Ice Barrier", "Ice Block", "Cold Snap"} <= pvp_core_talents(Consensus.load())


def test_pvp_score_prefers_the_pvp_variant_and_deep_frost():
    kits, consensus = load_kits(), Consensus.load()
    pvp = lambda ranks: class_pvp_score("mage", STATS, CLS, ranks, kits, consensus)
    assert pvp(B["elementalist-v4"]) > pvp(B["elementalist-pve"])
    assert pvp(B["deep-frost"]) > pvp(B["deep-fire"])


def test_pve_score_prefers_the_pve_variant():
    pve = lambda ranks: ms.pve_score("mage", STATS, CLS.spells, CLS, ranks)
    assert pve(B["elementalist-pve"]) > pve(B["elementalist-v4"])


def test_pvp_core_talents_are_the_class_s_own():
    assert pvp_core_talents(Consensus.load(), "mage") == pvp_core_talents(Consensus.load())
    assert pvp_core_talents(Consensus.load(), "hunter") == set()          # no Forever-era PvP evidence yet (#320)
