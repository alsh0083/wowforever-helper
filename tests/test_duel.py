"""Golden tests for the duel model (#26). Formulas: docs/tasks/26-duel.md; constants: config/duel.toml
(slow_kite_seconds 30, removal_factor 0.5, ranged_root_share 0.2, dispel_barrier_factor 0.5,
min_uptime 0.2, max_fight 600)."""

from pathlib import Path

import pytest

from wowforever.pvp.duel import Control, Kit, MageSide, duel, load_kits, mage_side, scenario_scores

BASE_MAGE = MageSide(health=3000, dps=150, barrier_per_min=0, immunity_share=0,
                     root=20, stun=0, slow=0.5, interrupt=20)
MELEE = Kit(id="test-melee", role="melee", stealth=False, dispels_buffs=False, health=4000, dps=200,
            opener_damage=900, opener_stun=4.0,
            controls=(Control("stun", 3, 30), Control("interrupt", 4, 10), Control("slow", 15, 0)),
            removes=(), immunity=None)


def test_kiting_melee_when_the_mage_sees_them():
    # mage uptime: 1 - (3*60/30 + 4*60/10)/60 = 1 - 30/60 = 0.5 (slows don't stop casting)
    # kite seconds K = root 20 + stun 0 + slow 0.5*30 = 35 -> opponent uptime 1 - 35/60
    # T_mage = 4000 / (150*0.5) = 53.333; T_opp = 3000 / (200*25/60) = 36
    r = duel(BASE_MAGE, MELEE, "mage_sees")
    assert r.mage_uptime == pytest.approx(0.5)
    assert r.opponent_uptime == pytest.approx(25 / 60)
    assert (r.t_mage, r.t_opponent) == pytest.approx((4000 / 75, 36.0))
    assert r.score == pytest.approx(36 / (36 + 4000 / 75))


def test_cheap_slow_and_root_removal_halves_kiting():
    kit = MELEE.__class__(**{**MELEE.__dict__, "removes": (("slow,root", 0),)})
    r = duel(BASE_MAGE, kit, "mage_sees")
    # K = 35 * 0.5 = 17.5 -> uptime 42.5/60; T_opp = 3000 / (200*42.5/60) = 21.176
    assert r.opponent_uptime == pytest.approx(42.5 / 60)
    assert r.t_opponent == pytest.approx(3000 / (200 * 42.5 / 60))


def test_barrier_absorbs_and_a_dispeller_halves_it():
    mage = MageSide(**{**BASE_MAGE.__dict__, "barrier_per_min": 600})
    kit = MELEE.__class__(**{**MELEE.__dict__, "dispels_buffs": True})
    # absorb 600/min = 10/s, halved by the dispel = 5/s; T_opp = 3000 / (83.333 - 5) = 38.298
    r = duel(mage, kit, "mage_sees")
    assert r.t_opponent == pytest.approx(3000 / (200 * 25 / 60 - 5))


def test_opener_when_they_open():
    # start damage = 900 + 4 s stun * 200 dps = 1700; T_opp = (3000 - 1700) / 83.333 = 15.6
    r = duel(BASE_MAGE, MELEE, "they_open")
    assert r.t_opponent == pytest.approx(1300 / (200 * 25 / 60))


def test_caster_uptime_comes_from_interrupts_and_stuns():
    caster = Kit(id="test-caster", role="caster", stealth=False, dispels_buffs=False, health=4000,
                 dps=200, opener_damage=0, opener_stun=0, controls=(Control("silence", 5, 45),),
                 removes=(), immunity=None)
    r = duel(BASE_MAGE, caster, "mage_sees")
    # opponent uptime 1 - (20 + 0)/60; mage uptime 1 - (5*60/45)/60
    assert r.opponent_uptime == pytest.approx(40 / 60)
    assert r.mage_uptime == pytest.approx(1 - (5 * 60 / 45) / 60)
    assert r.score == pytest.approx(22.5 / (22.5 + 4000 / (150 * r.mage_uptime)))


def test_ranged_physical_mostly_ignores_roots():
    hunter = Kit(id="test-ranged", role="ranged", stealth=False, dispels_buffs=False, health=4000,
                 dps=200, opener_damage=0, opener_stun=0, controls=(), removes=(), immunity=None)
    r = duel(BASE_MAGE, hunter, "mage_sees")
    assert r.opponent_uptime == pytest.approx(1 - (0 + 20 * 0.2) / 60)


def test_immunities_on_both_sides():
    mage = MageSide(**{**BASE_MAGE.__dict__, "immunity_share": 0.05})
    kit = MELEE.__class__(**{**MELEE.__dict__, "immunity": (12, 300)})
    r = duel(mage, kit, "mage_sees")
    assert r.t_mage == pytest.approx(4000 / (150 * 0.5 * (1 - 12 / 300)))
    assert r.t_opponent == pytest.approx(3000 / (200 * 25 / 60 * 0.95))


def test_uptime_floor_and_fight_cap():
    shut_down = MageSide(**{**BASE_MAGE.__dict__, "root": 120, "barrier_per_min": 100000})
    r = duel(shut_down, MELEE, "mage_sees")
    assert r.opponent_uptime == pytest.approx(0.2)
    assert r.t_opponent == pytest.approx(600)


# ---- real kits and builds ------------------------------------------------------------------


def test_shipped_kits_load():
    kits = load_kits()
    assert {k.id for k in kits} >= {"warrior-arms", "rogue-subtlety", "hunter-survival", "paladin-retribution",
                                    "priest-shadow", "shaman-enhancement", "warlock-affliction", "druid-feral"}
    assert all(k.health > 0 and k.dps > 0 for k in kits)


def test_scenario_scores_group_kits_by_role_and_stealth():
    kits = load_kits()
    s = scenario_scores(BASE_MAGE, kits)
    assert set(s) == {"wpvp_melee", "wpvp_melee_they_open", "wpvp_caster", "stealth_ambush"}
    melee = [k for k in kits if k.role == "melee"]
    assert s["wpvp_melee"]["score"] == pytest.approx(
        sum(duel(BASE_MAGE, k, "mage_sees").score for k in melee) / len(melee))
    assert set(s["stealth_ambush"]["matchups"]) == {k.id for k in kits if k.stealth}
    assert set(s["wpvp_caster"]["matchups"]) == {k.id for k in kits if k.role in ("caster", "ranged")}


def test_deep_frost_out_duels_deep_fire_against_melee():
    from wowforever.builds import load_builds
    from wowforever.classes.mage import LAYOUT, SKILL_LINES, TALENT_EFFECTS, UNMODELED
    from wowforever.effects import attach_effects
    from wowforever.normalize import normalize_class, read_tables
    from wowforever.normalize_spells import class_spells, ranks_of
    from wowforever.scenarios import Character
    from wowforever.sources.wowforevertalent import parse_page
    from wowforever.stats import StatTable
    fix = Path(__file__).parent / "fixtures"
    cls, _ = normalize_class(read_tables(fix / "wago-1.60.1.70205"), LAYOUT,
                             parse_page((fix / "wowforevertalent" / "mage.html").read_text(encoding="utf-8")),
                             wago_build="1.60.1.70205")
    cls, _ = attach_effects(cls, TALENT_EFFECTS, UNMODELED)
    spells = class_spells(read_tables(fix / "wago-1.60.1.70205-spells"), skill_lines=SKILL_LINES)
    builds = {b.id: b for b in load_builds(class_name="mage")}
    stats = StatTable.load("mage").at(60)

    def side(build_id, filler):
        char = Character(60, stats, spells, cls, builds[build_id].final_ids(cls))
        return mage_side(char, ranks_of(spells, filler)[-1])

    frost, fire = side("deep-frost", "Frostbolt"), side("deep-fire", "Fireball")
    kits = load_kits()
    assert scenario_scores(frost, kits)["wpvp_melee"]["score"] > scenario_scores(fire, kits)["wpvp_melee"]["score"]
