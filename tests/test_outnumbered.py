"""Outnumbered (2v1) world-PvP score (#278): a separate score next to the PvP score.

The defender sees both opponents coming (no openers) and kills them one at a time, in whichever
order scores better. Constants: config/duel.toml (min_uptime 0.2, max_fight 600, slow_kite_seconds 30,
dr_chain 1.75, dr_immune_seconds 15, outnumbered_control_split 0.5).

Phase 1, both opponents alive:
  defender uptime u1 = 1 - L(both)/60, where L adds both kits' lockout seconds per kind and caps each
  DR kind at 60 x 1.75 x d / (1.75 x d + 15) for the longest control d of that kind in either kit;
  t1 = first.health / (dps x u1); stuns, slows and interrupts are split 0.5 / 0.5 between the
  opponents; with one root target the root goes to the opponent not being attacked (damage breaks
  roots, #286), with two or more (Overgrowth) both are rooted. Incoming damage is each kit's DPS x
  its uptime against its share of control, as in a duel.
Phase 2, the second opponent alone: u2 = 1 - L(second)/60, t2 = second.health / (dps x u2), all
  control on it.
Defender's kill time T = t1 + t2. Time to die: if phase-1 damage x t1 reaches health, health /
  phase-1 damage; else t1 + (health - phase-1 damage x t1) / phase-2 damage. Score = T_die / (T + T_die).
Healing (budget B at H heal/s) happens in phase 1: it adds B / H seconds to phase 1 and to T, and B to
  health; it counts only if the score rises.

Kits: A melee, 3000 health, 100 DPS, no controls; B melee, 2000 health, 150 DPS, stun 4 s every 20 s
(12 s/min, under the cap 60 x 7 / 22 = 19.09). Defender: 4000 health, 200 DPS, root 20 s/min.

One root target, A first: u1 = 0.8, t1 = 3000 / 160 = 18.75; u2 = 0.8, t2 = 12.5; T = 31.25.
  Phase 1: A unrooted 100, B rooted 150 x 40/60 = 100; 3750 in 18.75 s, 250 left; phase 2 B rooted
  100: T_die = 18.75 + 2.5 = 21.25; score 21.25 / 52.5 = 0.404762.
One root target, B first: t1 = 12.5, t2 = 3000 / 200 = 15, T = 27.5. Phase 1: B 150 + A rooted
  66.667 = 216.667; 2708.333 in 12.5 s, 1291.667 left / 66.667 = 19.375; T_die = 31.875;
  score 31.875 / 59.375 = 0.536842. The pair scores 0.536842.
Three root targets (Overgrowth): B first, phase 1 100 + 66.667: 2083.333, left 1916.667 / 66.667 = 28.75;
  T_die = 41.25, score 41.25 / 68.75 = 0.6. A first: phase 1 66.667 + 100: 3125, left 875 / 100 = 8.75;
  T_die = 27.5, score 27.5 / 58.75 = 0.468085. The pair scores 0.6.
Stun 10 s/min and slow 0.2 too, A first: A gets root 0 + stun 5 + slow 0.1 x 30 = 8 s/min, 100 x 52/60 =
  86.667; B gets 20 + 5 + 3 = 28, 150 x 32/60 = 80; phase 1 166.667 x 18.75 = 3125, left 875; phase 2 B
  gets 20 + 10 + 6 = 36, 150 x 24/60 = 60: T_die = 18.75 + 14.583 = 33.333; score 33.333 / 64.583 = 0.516129.
Healing 2000 at 400/s (5 s): B first T = 32.5, phase 1 17.5 s x 216.667 = 3791.667 of 6000, left
  2208.333 / 66.667 = 33.125, T_die = 50.625, score 50.625 / 83.125 = 0.609023 (beats 0.536842).
  A first: T = 36.25, 23.75 x 200 = 4750, left 1250 / 100 = 12.5, T_die = 36.25, score 0.5. Pair 0.609023.
  Healing 1000 at 100/s doesn't help (B first: 0.393939 < 0.536842), so the pair stays 0.536842.
Death in phase 1 (2000 health): B first 2000 / 216.667 = 9.2308, score 9.2308 / 36.7308 = 0.251309;
  A first 2000 / 200 = 10, score 10 / 41.25 = 0.242424. Pair 0.251309.
Two stunners (B and a copy of it): 12 + 12 = 24 s/min of stuns, capped at 19.0909.
"""

import dataclasses

import pytest

from wowforever.classes.druid import TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.builds import load_builds
from wowforever.melee_scenarios import stat_table
from wowforever.classes import engine
from wowforever.pvp.class_pvp import class_side
from wowforever.pvp.duel import best_outnumbered
from wowforever.pvp.duel import Control, Kit, Side, combined_lockout, load_kits, outnumbered, outnumbered_scores
from wowforever.schema import Dataset, latest_dataset_path

A = Kit(id="a", role="melee", stealth=False, dispels_buffs=False, health=3000, dps=100, opener_damage=0,
        opener_stun=0, controls=(), removes=(), immunity=None)
B = Kit(id="b", role="melee", stealth=False, dispels_buffs=False, health=2000, dps=150, opener_damage=0,
        opener_stun=0, controls=(Control("stun", 4, 20),), removes=(), immunity=None)
SIDE = Side(health=4000, dps=200, absorb_per_min=0, immunity_share=0, root=20, stun=0, slow=0, interrupt=0)


def side(**changes):
    return dataclasses.replace(SIDE, **changes)


def pair(defender, x=A, y=B):
    return max(outnumbered(defender, x, y).score, outnumbered(defender, y, x).score)


def test_one_root_goes_to_the_opponent_not_being_attacked():
    first_a = outnumbered(SIDE, A, B)
    assert (first_a.t_side, first_a.t_opponent) == pytest.approx((31.25, 21.25))
    assert first_a.score == pytest.approx(0.404762, rel=1e-5)
    first_b = outnumbered(SIDE, B, A)
    assert (first_b.t_side, first_b.t_opponent) == pytest.approx((27.5, 31.875))
    assert first_b.score == pytest.approx(0.536842, rel=1e-5)


def test_overgrowth_roots_both_opponents():
    rooted = side(root_targets=3)
    assert outnumbered(rooted, B, A).score == pytest.approx(0.6)
    assert outnumbered(rooted, A, B).score == pytest.approx(0.468085, rel=1e-5)


def test_single_target_controls_split_between_opponents():
    assert outnumbered(side(stun=10, slow=0.2), A, B).score == pytest.approx(0.516129, rel=1e-5)


def test_healing_in_phase_one_counts_only_when_it_helps():
    assert pair(side(heal_hps=400, heal_budget=2000)) == pytest.approx(0.609023, rel=1e-5)
    assert outnumbered(side(heal_hps=400, heal_budget=2000), A, B).score == pytest.approx(0.5)
    assert pair(side(heal_hps=100, heal_budget=1000)) == pytest.approx(0.536842, rel=1e-5)


def test_dying_while_both_are_alive():
    assert outnumbered(side(health=2000), B, A).t_opponent == pytest.approx(2000 / (150 + 100 * 40 / 60))
    assert pair(side(health=2000)) == pytest.approx(0.251309, rel=1e-5)


def test_lockouts_add_up_under_one_dr_cap():
    assert combined_lockout([A, B]) == pytest.approx(12.0)
    assert combined_lockout([B, dataclasses.replace(B, id="b2")]) == pytest.approx(60 * 1.75 * 4 / (1.75 * 4 + 15))


def test_pairs_need_a_melee_opponent_and_take_the_better_kill_order():
    casters = [Kit(id=i, role="caster", stealth=False, dispels_buffs=False, health=3000, dps=120, opener_damage=0,
                   opener_stun=0, controls=(), removes=(), immunity=None) for i in ("c", "d")]
    result = outnumbered_scores(SIDE, [A, B, *casters])
    assert sorted(result["matchups"]) == ["a+b", "a+c", "a+d", "b+c", "b+d"]
    assert result["matchups"]["a+b"] == pytest.approx(0.536842, rel=1e-5)
    assert result["score"] == pytest.approx(sum(result["matchups"].values()) / 5)


CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("druid"), TALENT_EFFECTS, UNMODELED)
BUILDS = {b.id: b for b in load_builds(class_name="druid")}


def test_overgrowth_parses_and_sets_root_targets():
    assert PROBLEMS == []
    effects = [(e.kind, e.values, e.applies_to) for e in next(t for t in CLS.talents if t.name == "Overgrowth").effects]
    assert effects == [("targets", (1.0, 2.0), ("Entangling Roots",))]
    ranks = BUILDS["druid-balance-pvp-leveling"].final_ids(CLS)  # the model pick drops Overgrowth
    stats = stat_table("druid").at(60)
    assert class_side("druid", stats, CLS.spells, CLS, ranks).root_targets == 3
    overgrowth = next(t.talent_id for t in CLS.talents if t.name == "Overgrowth")
    without = {**ranks, overgrowth: 0}
    assert class_side("druid", stats, CLS.spells, CLS, without).root_targets == 1
    kits = load_kits()
    assert (best_outnumbered(engine("druid").sides(stats, CLS.spells, CLS, ranks), kits)[0]
            > best_outnumbered(engine("druid").sides(stats, CLS.spells, CLS, without), kits)[0])
