"""Golden tests for survival and control scoring (#25) on real fixture data at level 60.

Spell values (fixture rows): Ice Barrier r4 absorbs 811, 30 s cooldown; Ice Block 10 s immunity,
300 s cooldown; Cold Snap 600 s; Frost Nova r4 roots 8 s, 25 s cooldown; Blink 15 s; Counterspell
10 s lockout, 30 s cooldown; Frostbolt r11 3.0 s cast, 9 s chill at 40%; Fireball r12 3.5 s cast.
Talent text at max rank: Permafrost +33% chill duration, +10% slow; Improved Frost Nova -4 s;
Frostbite 15% freeze for 5 s; Impact 10% stun for 2 s; Burning Soul 70%; Improved Counterspell
4 s silence. Weights/references are config/pvp_axes.toml.
"""

from pathlib import Path

import pytest

from wowforever.builds import load_builds
from wowforever.calc.pvp_axes import control, survival
from wowforever.classes.mage import LAYOUT, SKILL_LINES, TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.normalize import normalize_class, read_tables
from wowforever.normalize_spells import class_spells, ranks_of
from wowforever.scenarios import Character
from wowforever.sources.wowforevertalent import parse_page
from wowforever.stats import Stats

FIX = Path(__file__).parent / "fixtures"
RAW, _ = normalize_class(read_tables(FIX / "wago-1.60.1.70205"), LAYOUT,
                         parse_page((FIX / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                         wago_build="1.60.1.70205")
CLS, REPORT = attach_effects(RAW, TALENT_EFFECTS, UNMODELED)
SPELLS = class_spells(read_tables(FIX / "wago-1.60.1.70205-spells"), skill_lines=SKILL_LINES)
# the owner's former hand-made Elementalist builds stay as fixtures (tests/fixtures/builds/)
BUILDS = {b.id: b for b in [*load_builds(class_name="mage"), *load_builds(Path(__file__).parent / "fixtures" / "builds", class_name="mage")]}
STATS = Stats(60, intellect=270, spirit=190, stamina=220, spell_power=150, crit_pct=6, hit_pct=3,
              mana=3600, health=2900)
FROSTBOLT = ranks_of(SPELLS, "Frostbolt")[-1]
FIREBALL = ranks_of(SPELLS, "Fireball")[-1]


def char(build_id):
    return Character(60, STATS, SPELLS, CLS, BUILDS[build_id].final_ids(CLS))


def test_new_effect_rules_parse_cleanly():
    assert REPORT == []
    for name in ("Permafrost", "Improved Frost Nova", "Frostbite", "Improved Counterspell"):
        assert CLS.talent_named(name).effects, name


def test_deep_frost_survival():
    # barrier: 811 * 60/30 = 1622 per min / 2900 health = 0.5593 -> share min(1, /0.5) = 1
    # immunity: Ice Block 600/300 = 2 uses + 1 Cold Snap reset = 3 per 10 min -> 3*10/600 = 0.05 -> 1
    # pushback: Frostbolt filler (no Burning Soul) + Ice Barrier 0.5 -> 0.5 -> share 0.5
    # escapes: Blink 60/15 = 4 + Frost Nova 60/(25-4) = 2.857 -> 6.857 / 8 = 0.857
    # score = .35*1 + .25*1 + .20*.5 + .20*.857 = 0.8714
    s = survival(char("deep-frost"), FROSTBOLT)
    assert s.components["barrier"] == pytest.approx(1622 / 2900)
    assert s.components["immunity"] == pytest.approx(0.05)
    assert s.components["pushback"] == pytest.approx(0.5)
    assert s.components["escapes"] == pytest.approx(4 + 60 / 21)
    assert s.score == pytest.approx(0.35 + 0.25 + 0.20 * 0.5 + 0.20 * (4 + 60 / 21) / 8)


def test_deep_frost_control():
    # Frostbolt cast 3.0 - 0.5 (Improved Frostbolt) = 2.5 s per chill
    # slow: chill 9 * 1.33 = 11.97 s >= 2.5 -> uptime 1; strength (40 + 10)/100 -> 0.5 -> share 1
    # root: Frost Nova 8 * 60/21 = 22.857 + Frostbite 0.15 * (60/2.5) * 5 = 18 -> 40.857 s/min -> 1
    # stun: no Impact -> 0
    # interrupt: Counterspell 10 s per 30 s = 20 s/min (no Improved Counterspell) -> 1
    # score = .35 + .35 + 0 + .15 = 0.85
    c = control(char("deep-frost"), FROSTBOLT)
    assert c.components["slow"] == pytest.approx(0.5)
    assert c.components["root"] == pytest.approx(8 * 60 / 21 + 0.15 * 24 * 5)
    assert c.components["stun"] == 0
    assert c.components["interrupt"] == pytest.approx(20)
    assert c.score == pytest.approx(0.85)


def test_elementalist_with_a_fire_filler():
    # Fireball 3.5 - 0.5 (Improved Fireball) = 3.0 s -> 20 fire hits/min; Fireball doesn't chill
    # survival: no barrier; immunity 0.05 -> 1; pushback Burning Soul 0.70 (fire filler) -> 0.7;
    #   escapes 4 + 60/25 = 6.4 -> 0.8  => .25 + .20*.7 + .20*.8 = 0.55
    # control: slow 0; root Frost Nova 8*60/25 = 19.2 (Frostbite needs chills) -> 0.64;
    #   stun Impact 0.10 * 20 * 2 = 4 s/min -> 4/6; interrupt 20 -> 1
    #   => .35*.64 + .15*(4/6) + .15 = 0.474
    s = survival(char("elementalist-pve"), FIREBALL)
    assert s.components["pushback"] == pytest.approx(0.7)
    assert s.score == pytest.approx(0.25 + 0.20 * 0.7 + 0.20 * 0.8)
    c = control(char("elementalist-pve"), FIREBALL)
    assert c.components["stun"] == pytest.approx(4)
    assert c.components["root"] == pytest.approx(19.2)
    assert c.score == pytest.approx(0.35 * 0.64 + 0.15 * 4 / 6 + 0.15)


def test_improved_counterspell_adds_silence():
    ranks = dict(BUILDS["deep-frost"].final_ids(CLS))
    ranks[CLS.talent_named("Improved Counterspell").talent_id] = 2
    c = control(Character(60, STATS, SPELLS, CLS, ranks), FROSTBOLT)
    assert c.components["interrupt"] == pytest.approx((10 + 4) * 60 / 30)


def test_spells_not_learned_yet_dont_count():
    # level 20: no Ice Barrier (learned 40), no Counterspell (24)
    c20 = Character(20, STATS, SPELLS, CLS, {})
    s = survival(c20, ranks_of(SPELLS, "Frostbolt")[3])
    assert s.components["barrier"] == 0
    assert control(c20, ranks_of(SPELLS, "Frostbolt")[3]).components["interrupt"] == 0
