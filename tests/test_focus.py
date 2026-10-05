"""Focus scores (#28) on the real fixtures: direction checks, not golden values."""

from pathlib import Path

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.classes.mage import LAYOUT, SKILL_LINES, TALENT_EFFECTS, UNMODELED
from wowforever.consensus import Consensus
from wowforever.effects import attach_effects
from wowforever.focus import pve_score_fn, pvp_core_talents, pvp_score_fn
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells
from wowforever.pvp.duel import load_kits
from wowforever.sources.wowforevertalent import parse_page
from wowforever.stats import StatTable
from dataclasses import replace

FIX = Path(__file__).parent / "fixtures"
CLS, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205"), LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
CLS, _ = attach_effects(CLS, TALENT_EFFECTS, UNMODELED)
CLS = replace(CLS, spells=class_spells(read_tables(FIX / "wago-1.60.1.70205-spells"), skill_lines=SKILL_LINES))
B = {b.id: b.final_ids(CLS) for b in load_builds()}
STATS, A = StatTable.load("mage").at(60), Assumptions.load()


def test_archetype_config():
    arch = Consensus.load().archetypes
    assert (arch["deep"], arch["hybrid"]) == (31, 15) and "Fire/Frost" in arch["recognized"]


def test_pvp_core_talents_come_from_consensus_tiers():
    assert {"Ice Barrier", "Ice Block", "Cold Snap"} <= pvp_core_talents(Consensus.load())


def test_pvp_score_prefers_the_pvp_variant_and_deep_frost():
    pvp = pvp_score_fn(CLS, STATS, A, load_kits(), Consensus.load())
    assert pvp(B["elementalist-v4"]) > pvp(B["elementalist-pve"])
    assert pvp(B["deep-frost"]) > pvp(B["deep-fire"])


def test_pve_score_prefers_the_pve_variant():
    pve = pve_score_fn(CLS, STATS, A)
    assert pve(B["elementalist-pve"]) > pve(B["elementalist-v4"])
